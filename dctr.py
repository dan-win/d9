"""
"""
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
        return repr(self.value)  

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

    >>> e1 = Environment({a=1, b='string'})

    >>> e2 = Environment()
    >>> e1.extendfrom(e2)

    """

    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)


    def extendfrom(self, source):
        """
        Apply all public fields and their values 
        from other "environment" (swallow copy).
        Note that "source" can be object of
        any type (e.g., named tuple).
        """

        attr_names = dir(source)

        for name in attr_names:
            # private or protected attr:
            if attr.startswith('_'): 
                continue
            # Bypass complex type(s)
            attr = getattr(self, name)
            if isinstance(attr, (
                TYPE_LIST, TYPE_DICT, TYPE_OBJ)):
                continue
            # extract value if attribute is "computed value":
            if isinstance(attr, TYPE_FUNC):
                value = value()
            # create attr in target env
            # and copy value
            setattr(self, name, value)

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
    
    @staticmethod
    def help():
        """
        Print hint about usage.
        """
        return \
        """ 
        Not all arguments specified.
        Usage:
        <scriptname> total=<value> idle=<integer>
            Where:
            total: total number of agents
            idle: number of idle agents
        """
        
    def __init__(self):
        import sys
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
        try:
            self.total_agents = data["total"]
            self.idle_agents = data["idle"]
        except KeyError:
            # Print hint and exit:
            raise ECliError(self.help())


class PIEnvironment(Environment):

    def __init__(self, **kwargs):
        Environment.__init__(self, **kwargs)
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
        pass

##############################################
# SOLVER classes
##############################################
# *** Basic solver (abstract, protocol only) ***
class Solver(object):
    """
    Abstract class, base for solvers.
    Defines main protocol methods
    """
    requires = []

            
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
                    "Environment is not corresponds to solver: required attribute '{}' missed!".format(key))
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

        'total_agents',
        'idle_agents',

        # add query functions with parameters (qty, time) with selectable depth

        # here is 5-minutes depth
        'calls_total', # all outbound calls
        'calls_answered', # served + abandoned
        'calls_congested', # rejected calls due to network overload
        'calls_served', # call processed by agents

        'uptime', # uptime in seconds
        'interval' # interval from last call in seconds
    ]
    
    def __init__(self):
        self.integrator = 0
    
    def predict_outgoing_calls(self):
        import math
        
        e = self.e
        
        if e.idle_agents < e.min_idle_agents:
            # return zero and wait while min_idle_agents will be available
            # otherwise we alway in progressive mode!
            return 0

        # Switch to pregressive mode:
        if e.uptime < e.uptime_threshold or \
            e.calls_answered < e.calls_threshold or\
            e.predict_adjust == 0:
            return ProgressiveSolver.predict_outgoing_calls(self) 

        # if current abandoned cals > 3% - switch to progressive mode
        n_abandoned_calls = float (e.calls_answered - e.calls_served) / e.calls_answered
        if n_abandoned_calls > e.max_abandon_calls:
            return ProgressiveSolver.predict_outgoing_calls(self) 

        over_dial = 0
        try:
            connection_rate = e.calls_answered / e.calls_total
            over_dial = float(e.idle_agents)/connection_rate - e.idle_agents
        except ZeroDivisionError:
            return e.idle_agents

        # tune predict_adjust
        deviation = n_abandoned_calls - e.target_abandon_calls
        
        P_value = e.ctr_proportional_gain * deviation

        self.integrator = self.integrator + deviation

        #~ if self.integrator > 500:
                #~ self.integrator = 500
        #~ elif self.integrator < -500:
                #~ self.integrator = -500

        I_value = self.integrator * e.ctr_integral_gain

        e.predict_adjust = e.predict_adjust + (P_value + I_value) * 10        
        

        calls_to_dial = math.trunc(e.idle_agents + (over_dial * e.predict_adjust) * 0.01)

        return calls_to_dial 


def main():
    env = PIEnvironment()
    input = CLIEnvironment()
    env.extendfrom(input)    
    s = PIController()
    s.observe(env)
    print s.predict_outgoing_calls()

if __name__ == "__main__":
    main()


