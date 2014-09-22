# -*- coding: utf-8 -*-
#
# Component base class for ETL.
#
# Author: Just van den Broecke
#
from util import Util, ConfigSection
from packet import FORMAT

log = Util.get_log('component')

class Config(object):
    """
    Decorator class to tie config values from the .ini file to object instance
    property values. Somewhat like the Python standard @property but with
    the possibility to define default values, typing and making properties required.

    Each property is defined by @Config(type, default, required).
    Basic idea comes from:  https://wiki.python.org/moin/PythonDecoratorLibrary#Cached_Properties
    """
    def __init__(self, python_type=str, default=None, required=False):
        """
        If there are no decorator arguments, the function
        to be decorated is passed to the constructor.
        """
        # print "Inside __init__()"
        self.python_type = python_type
        self.default = default
        self.required = required

    def __call__(self, fget):
        """
        The __call__ method is not called until the
        decorated function is called. self is returned such that __get__ below is called
        with the Component instance. That allows us to cache the actual property value
        in the Component itself.
        """
        # print "Inside __call__()"
        self.property_name = fget.__name__
        return self

    def __get__(self, comp_inst, owner):
        if self.property_name not in comp_inst.cfg_vals:
            cfg, name, value = comp_inst.cfg, self.property_name, self.default

            # Do type conversion where needed from the string values
            if self.python_type is str:
                value = cfg.get(name, value)
            elif self.python_type is bool:
                value = cfg.get_bool(name, value)
            elif self.python_type is list:
                value = cfg.get_list(name, value)
            elif self.python_type is dict:
                value = cfg.get_dict(name, value)
            elif self.python_type is int:
                value = cfg.get_int(name, value)
            elif self.python_type is tuple:
                value = cfg.get_tuple(name, value)
            else:
                value = cfg.get(name, value)

            if self.required is True and value is None:
                raise Exception('Config property: %s is required in config for %s' % (name, str(comp_inst)))

            comp_inst.cfg_vals[self.property_name] = value

        return comp_inst.cfg_vals[self.property_name]


class Component:
    """
    Abstract Base class for all Input, Filter and Output Components.

    """

    @Config(str, default=None, required=False)
    def input_format(self):
        """
        The specific input format if the consumes parameter is a list or the format to be converted to the output_format.
        Required: False
        Default: None
        """
        pass

    @Config(str, default=None, required=False)
    def output_format(self):
        """
        The specific output format if the produces parameter is a list or the format to which the input format is converted.
        Required: False
        Default: None
        """
        pass

    def __init__(self, configdict, section, consumes=FORMAT.none, produces=FORMAT.none):
        # The raw config values from the cfg file
        self.cfg = ConfigSection(configdict.items(section))

        # The actual typed values as populated within Config Decorator
        self.cfg_vals = dict()
        self.next = None

        # Some components may have multiple output formats: in that case either a
        # specific output_format needs to be configured or the first format is taken as default
        self._output_format = produces
        if type(produces) is list:
            if self.cfg.has('output_format'):
                self._output_format = self.cfg.get('output_format')
                if self._output_format not in produces:
                    raise ValueError(
                        'Configured output format %s not in list: %s' % (self._output_format, str(produces)))
            else:
                self._output_format = produces[0]

        # Some components may have multiple input formats: in that case either a
        # specific output_format needs to be configured or the first format is taken as default
        self._input_format = consumes
        if type(consumes) is list:
            if self.cfg.has('input_format'):
                self._input_format = self.cfg.get('input_format')
                if self._input_format not in consumes:
                    raise ValueError('Configured input format %s not in list: %s' % (self._input_format, str(consumes)))
            else:
                self._input_format = consumes[0]

    def add_next(self, next_component):
        self.next = next_component

        if not self.is_compatible():
            raise ValueError(
                'Incompatible components linked: %s and %s' % (str(self), str(self.next)))

    # Check our compatibility with the next Component in the Chain
    def is_compatible(self):
        # Ok, nothing next in Chain
        if self.next is None or self._output_format is FORMAT.none or self.next._input_format == FORMAT.any:
            return True

        # return if our Output is compatible with the next Component's Input
        return self._output_format == self.next._input_format

    def __str__(self):
        return "%s: in=%s out=%s" % (str(self.__class__), self._input_format, self._output_format)

    def process(self, packet):

        # Do something with the data
        result = self.before_invoke(packet)
        if result is False:
            # Component indicates it does not want the chain to proceed
            return packet

        # Do component-specific processing, e.g. read or write or filter
        packet = self.invoke(packet)

        result = self.after_invoke(packet)
        if result is False:
            # Component indicates it does not want the chain to proceed
            return packet

        # If there is a next component, let it process
        if self.next:
            # Hand-over data (line, doc whatever) to the next component
            packet.format = self._output_format
            packet = self.next.process(packet)

        result = self.after_chain_invoke(packet)
        return packet

    def do_init(self):
        # Some components may do one-time init
        self.init()

        # If there is a next component, let it do its init()
        if self.next:
            self.next.do_init()

    def do_exit(self):
        # Notify all comps that we exit
        self.exit()

        # If there is a next component, let it do its exit()
        if self.next:
            self.next.do_exit()

    def before_invoke(self, packet):
        """
        Called just before Component invoke.
        """
        return True

    def after_invoke(self, packet):
        """
        Called right after Component invoke.
        """
        return True

    def after_chain_invoke(self, packet):
        """
        Called right after entire Component Chain invoke.
        """
        return True

    def invoke(self, packet):
        """
        Components override for Component-specific behaviour, typically read, filter or write actions.
        """
        return packet

    def init(self):
        """
        Allows derived Components to perform a one-time init.
        """
        pass

    def exit(self):
        """
        Allows derived Components to perform a one-time exit/cleanup.
        """
        pass

