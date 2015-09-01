# fix division problem:
from __future__ import division
##############################################
# Exceptions
##############################################
class ESolverError(Exception):
    """
    Generic error type in module
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return str(self.value)  

class EEnvironmentError(ESolverError):
    """
    Invalid incoming data
    """
    pass
    
class ECliError(EEnvironmentError):
    """
    Invalid arguments from CLI
    """
    pass

##############################################
# ENVIRONMENT SNAPSHOT classes
##############################################

"""
Constants
"""
def ftype(): pass
TYPE_STRING = type("abc")
TYPE_BOOL = type(False)
TYPE_LIST = type([])
TYPE_DICT = type({})
TYPE_OBJ = type(object)
TYPE_FUNC = type(ftype)


class Environment(object):
    """ 
    Base class for set of queries and constants.
    Can be "extended" from other instance by copying
    values of attributes (so values from several models 
    can be joined to the single composite model).

    Atrributes with other types or any 'private/protected'
    attribute (started with '_') will be ignored. 

    Supported type of attrs: string, numeric, 
    boolean, function (from latter its' result
    is extracted).

    Sample:

    >>> e1 = Environment(a=1, b='string', c=True, d=0.1)
    >>> e1.dump()
    ['a:1', 'b:string', 'c:True', 'd:0.1']
    >>> e2 = Environment()
    >>> e1.extendfrom(e2).dump()
    ['a:1', 'b:string', 'c:True', 'd:0.1']
    """

    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)

    def _enumownprops(self):
        import numbers
        buff = []
        attr_names = dir(self)

        for name in attr_names:
            # private or protected attr:
            if name.startswith('_'): 
                continue
            # Bypass complex type(s)
            value = getattr(self, name)
            if isinstance(value, (numbers.Number, TYPE_STRING,)):
                buff.append(name)
        buff.sort()
        return buff

    def dump(self):
        attr_names = self._enumownprops()
        buff=[]
        for name in attr_names:
            if name.startswith('_'):
                continue
            buff.append('{0}:{1}'.format(name, getattr(self, name)))
        return buff
        
    
    def extendfrom(self, source):
        """
        Apply all public fields and their values 
        from other "environment" (swallow copy).
        Note that "source" can be object of
        any type (e.g., named tuple).
        """
        if not isinstance(source, Environment):
            raise EEnvironmentError( \
                '.extendfrom() argument must be an Environment instance!')
            
        attr_names = source._enumownprops()

        for name in attr_names:
            # private or protected attr:
            if name.startswith('_'): 
                continue
            # Bypass complex type(s)
            value = getattr(source, name)
            # to-do:
            #~ # extract value if attribute is "computed value":
            #~ if isinstance(value, TYPE_FUNC):
                #~ value = value()
            # create attr in target env
            # and copy value
            setattr(self, name, value)
        
        # for chaining:
        return self 
        # end of "extend"

class CLIEnvironment(Environment):
    """
    Datamodel with CLI source.
    Extracts data from arguments 
    in command line.
    Arguments list must be in format:
    <name>=<value>
    """
    
    required = [
        'idle_agents',

        # add query functions with parameters (qty, time) with selectable depth

        # here is 5-minutes depth
        'calls_total', # all outbound calls
        'calls_answered', # served + abandoned
        #~ 'calls_congested', # rejected calls due to network overload
        'calls_served', # call processed by agents

        'uptime', # uptime in seconds
        'interval' # interval from last call in seconds
    ]
    
    hint = {
        'idle_agents': 'Number of idle (free) agents',

        # add query functions with parameters (qty, time) with selectable depth

        # here is 5-minutes depth
        'calls_total': 'All dialed outbound calls (integer)', # all outbound calls
        'calls_answered': 'All answered calls (including voicemal, fax)  (integer)', # served + abandoned
        #~ 'calls_congested', # rejected calls due to network overload
        'calls_served': 'Calls processed by agents  (integer)',

        'uptime': 'Uptime of call center in seconds',
        'interval': 'Observed nterval from in seconds'
    }
    
    @staticmethod
    def help():
        """
        Print hint about usage.
        """
        arg_hints = [': '.join((k, v)) for k, v in CLIEnvironment.hint.items()]
        return \
    """ 
Not all arguments specified.
Usage:
<scriptname> {}

Where:
\t{}
        """.format( \
            ' '.join(['{}=<value>'.format(name) for name in CLIEnvironment.required]), \
            '\n\t'.join(arg_hints))
        
    def __init__(self, **kwargs):
        Environment.__init__(self, **kwargs)
        try:
            import sys
        except ImportError:
            raise ECliError(
                'Module "sys" is not available.\nCommand-line option disabled.')
        args = sys.argv
        data = {}
        
        # parse arg text and perform type conversion:
        for pair in args[1:]: 
            try:
                # ^ bypass the first arg, it is script name
                name, value = pair.split("=")
                value = value.strip(" ") # remove spaces
                data[name] = int(value)
            except ValueError:
                # value cannot be converted to integer
                raise ESolverInputError(
                    "Argument value must be an integer number!")
        
        # Extract values from parsed arg text:
        for name in CLIEnvironment.required:
            try:
                setattr(self, name, data[name])
            except KeyError:
                # Print hint and exit:
                print self.help()
                sys.exit()

class PIEnvironment(Environment):

    def __init__(self, **kwargs):
        # Set default constants:
        self.ctr_integral_gain = 0.05
        self.ctr_proportional_gain = 2.0
        self.predict_adjust = 150.0

        self.uptime_threshold = 5 * 60 # 5 minutes
        self.calls_threshold = 10
        self.min_idle_agents = 3

        self.target_abandon_calls = 2.5 / 100 # %
        self.max_abandon_calls = 3.0 /100 # %
        # set default values:

        #~ self.total_agents = 0
        self.idle_agents = 0

        self.calls_total = 0 # all outbound calls
        self.calls_answered = 0 # served + abandoned
        #~ self.calls_congested = 0 # rejected calls due to network overload
        self.calls_served = 0 # call processed by agents

        self.uptime = 0 # uptime in seconds
        self.interval = 1 # interval from last call in seconds
        
        # constructor call must be at the end,
        # othwervise **kwarg values will be lost:
        Environment.__init__(self, **kwargs)


##############################################
# SOLVER classes
##############################################
# *** Basic solver (abstract, protocol only) ***
class Solver(object):
    """
    Abstract class, base for solvers.
    Defines main protocol methods
    """
    required = []

    def __init__(self, environment=None):
        self.e = None
        if environment:
            self.observe(environment)
            
    def observe(self, environment):
        """ 
        Fill own properties by actual values from environment.
        Update computed properties.
        """
        self.e = environment
        # Check presence of required attrs:
        for key in self.required:
            if not hasattr(self.e, key):
                raise ESolverError(
                    "Environment does not correspond to solver:\n required attribute '{}' missed!".format(key))
        pass
        
    def predict_outgoing_calls(self):
        """
        Main method which return(s)
        recommended number of outgoing calls 
        """
        raise NotImplemented()

# *** Progressive sollver ***
class ProgressiveSolver(Solver):

    def predict_outgoing_calls(self):
        # one call per idle agent:
        return self.e.idle_agents
        
# *** Predictive solver ***
class PIController(ProgressiveSolver):
    """
    >>> e = PIEnvironment(idle_agents=10,calls_total=1000,calls_answered=300,calls_served=299,uptime=1000,interval=300)
    >>> c = PIController(e)
    >>> c.e.dump()
    ['calls_answered:300', 'calls_served:299', 'calls_threshold:10', 'calls_total:1000', 'ctr_integral_gain:0.05', 'ctr_proportional_gain:2.0', 'idle_agents:10', 'interval:300', 'max_abandon_calls:0.03', 'min_idle_agents:3', 'predict_adjust:150.0', 'target_abandon_calls:0.025', 'uptime:1000', 'uptime_threshold:300']

    >>> c.predict_outgoing_calls()
    10
    """

    required = [
        # set default values:
        'ctr_integral_gain',
        'ctr_proportional_gain',
        'predict_adjust',

        'uptime_threshold', # swith to predictive if passed
        'calls_threshold', # swith to predictive if passed
        'min_idle_agents',    
        'target_abandon_calls',
        'max_abandon_calls',

        #~ 'total_agents',
        'idle_agents',

        # add query functions with parameters (qty, time) with selectable depth

        # here is 5-minutes depth
        'calls_total', # all outbound calls
        'calls_answered', # served + abandoned
        #~ 'calls_congested', # rejected calls due to network overload
        'calls_served', # call processed by agents

        'uptime', # uptime in seconds
        'interval' # interval from last call in seconds
    ]
    
    def __init__(self, environment=None):
        ProgressiveSolver.__init__(self, environment)
        self.integrator = 0
        self.lasterror = ''
    
    def predict_outgoing_calls(self, debug=False):
        def _trace(msg=None): 
            if debug: 
                print msg or self.lasterror
        
        import math
        
        e = self.e
        
        #~ _trace('\nActual values for environment:')
        #~ _trace('\n'.join(e.dump()))
        #~ _trace('\n')
        
        # Validate dataset values
        if e.calls_total < e.calls_answered:
            self.lasterror = 'Critical error: e.calls_total < e.calls_answered'
            _trace()
            raise ESolverError(self.lasterror)
        
        # Handle values below threshold(s):
        
        if e.idle_agents < e.min_idle_agents:
            # return zero and wait while min_idle_agents will be available
            # otherwise we always in progressive mode!
            self.lasterror = 'uptime below threshold'
            _trace()
            return 0

        # Switch to pregressive mode in the following cases:
        if e.uptime < e.uptime_threshold:
            self.lasterror = 'uptime below threshold'
            _trace()
            return ProgressiveSolver.predict_outgoing_calls(self)
            
        if e.calls_answered < e.calls_threshold:
            self.lasterror = 'calls_answered below threshold'
            _trace()
            return ProgressiveSolver.predict_outgoing_calls(self) 
            
        if e.predict_adjust == 0:
            self.lasterror = 'predict_adjust is 0'
            _trace()
            return ProgressiveSolver.predict_outgoing_calls(self) 

        # if current abandoned cals > 3% - switch to progressive mode
        n_abandoned_calls = float (e.calls_answered - e.calls_served) / e.calls_answered
        _trace('abandoned rate={}'.format(n_abandoned_calls))
        
        if n_abandoned_calls > e.max_abandon_calls:
            self.lasterror = 'n_abandoned_calls over threshold'
            _trace()
            return ProgressiveSolver.predict_outgoing_calls(self) 

        connection_rate, over_dial = 0, 0
        try:
            connection_rate = float(e.calls_answered) / e.calls_total
        except ZeroDivisionError:
            self.lasterror = 'calls_total is zero'
            _trace()
            return ProgressiveSolver.predict_outgoing_calls(self) 
        
        try:
            over_dial = float(e.idle_agents)/connection_rate - e.idle_agents
        except ZeroDivisionError:
            self.lasterror = 'connection_rate is zero'
            _trace()
            return ProgressiveSolver.predict_outgoing_calls(self) 

        # tune predict_adjust
        deviation = e.target_abandon_calls - n_abandoned_calls 
        _trace('deviation={}'.format(deviation))
        
        P_value = e.ctr_proportional_gain * deviation
        _trace('P_value={}'.format(P_value))

        self.integrator = self.integrator + deviation
        _trace('self.integrator={}'.format(self.integrator))

        #~ if self.integrator > 500:
                #~ self.integrator = 500
        #~ elif self.integrator < -500:
                #~ self.integrator = -500

        I_value = self.integrator * e.ctr_integral_gain
        _trace('I_value={}'.format(I_value))

        e.predict_adjust = e.predict_adjust + (P_value + I_value) #* 100        
        _trace('e.predict_adjust={}'.format(e.predict_adjust))

        calls_to_dial = math.trunc(e.idle_agents + (over_dial * e.predict_adjust) * 0.01)

        return calls_to_dial 

if __name__ == "__main__":
    import doctest
    doctest.testmod()

