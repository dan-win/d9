from khronos.des import Simulator, Process, Chain, Signal, Listener
from khronos.des.extra.components.resources import Resource
from khronos.statistics import TSeries, Plotter

import numpy

import dctr as predict

class Call(Process):
    """Represents simulated environment of incoming calls"""
    
    # settings
    ctr_integral_gain = 0.05
    ctr_proportional_gain = 2.0
    predict_adjust = 150.0

    # criterions for progressive mode:
    uptime_threshold = 5 * 60 # 5 minutes in seconds
    calls_threshold = 10
    min_idle_agents = 3    
    
    target_abandon_calls = 2.5 / 100 # %
    max_abandon_calls = 3.0 /100 # %
    
    # state definition:
    total_agents = None # will be assigned from model
    idle_agents = None # will be assigned from model
    
    calls_total = 0 # total outbound calls
    calls_answered = 0 # total answered
    calls_congested = 0 # due to network overload, to-do
    calls_served = 0 # total served, abandon = calls_answered-calls_served
    
    uptime = 0
    interval = 0
    # the settings above will be overriden by CallCenterSim.reset()!
    
    # simulation settings:
    p_answer = 0.2 # 20% probability of a live call response
        
    talk_time_min = 10.0 * 60 # 10 minutes
    talk_time_max = 20.0 * 60 # 20 minutes
    
    predicted_calls = 0
    
    def is_answered(self):
        p = self.sim.rng.uniform(0, 1)
        if p < Call.p_answer:
            return True
        return False

    def service_time(self):
        # assume uniform distribution for call duration
        # to-do: poisson or erlang distribution (?)
        #~ return self.sim.rng.uniform(Call.talk_time_min, Call.talk_time_max)
        return numpy.random.poisson(70)

    @Chain
    def initialize(self):
        # Update "uptime"
        Call.uptime = int(self.sim.time) # convert to seconds (for solver)
        # Count calls:
        Call.calls_total += 1
        
        # If call answered:
        if self.is_answered():
            # Update counter for answered call
            Call.calls_answered += 1
            # serve call if agent is available:
            if Call.idle_agents > 0:
                # aquire agent:
                Call.idle_agents -= 1
                # wait until conversation finished:
                yield self.service_time()
                # release agent:
                Call.idle_agents += 1
                # update served count:
                Call.calls_served +=1
                yield Signal("AgentIsIdle")

        pass # end                

#~ class Agent(Process):
    
    #~ talk_time_min = 10.0 / 60 # 10 minutes
    #~ talk_time_max = 20.0 / 60 # 20 minutes
    
    #~ def service_time(self):
        #~ # assume uniform distribution for call duration
        #~ # to-do: poisson or erlang distribution (?)
        #~ return self.sim.rng.uniform(Agent.talk_time_min, Agent.talk_time_max)
        
    #~ @Chain
    #~ def initialize(self):
        #~ self.idle_time = 0
    
    

class CallCenterSim(Simulator):
    """Generates customer traffic and resets 'served' and 'happy' counters at initialization."""
    #~ rate = 40.0 # clients per hour (arrival rate)
    rate = 2 # outbound calls per second
    
    total_agents = 0
    
    solver = predict.PIController()

    def reset(self):
        Call.autoname_reset()

        Call.ctr_integral_gain = 0.05
        Call.ctr_proportional_gain = 2.0
        Call.predict_adjust = 150.0

        # criterions for progressive mode:
        Call.uptime_threshold = 5 * 60 # 5 minutes in seconds
        Call.calls_threshold = 10
        Call.min_idle_agents = 3    
        
        Call.target_abandon_calls = 3.0 /100 # % 2.5 / 100 # %
        Call.max_abandon_calls = 3.0 /100 # %
        
        # state definition:
        total_agents = CallCenterSim.total_agents 
        Call.total_agents = total_agents 
        Call.idle_agents = total_agents 
        Call.predicted_calls = total_agents 
        
        Call.calls_total = 0 # total outbound calls
        Call.calls_answered = 0 # total answered
        Call.calls_congested = 0 # due to network overload, to-do
        Call.calls_served = 0 # total served, abandon = calls_answered-calls_served
        
        Call.uptime = 0
        
        CallCenterSim.solver.observe(Call)

    @Chain
    def initialize(self):
        # start process:        
        while True:
            #~ for i in range(0, Call.predicted_calls):
                #~ self.launch(Call())        
                #~ yield 5.0/3600
                #~ yield (1.0/rate)/3600
            #~ yield Listener('AgentIsIdle')  
            #~ Call.predicted_calls = CallCenterSim.solver.predict_outgoing_calls()


            self.launch(Call())
            yield 1/CallCenterSim.rate
            #~ yield self.rng.expovariate(CallCenterSim.rate)


def compute_abandoned():
    try:
        return float(Call.calls_answered - Call.calls_served) / Call.calls_answered
    except ZeroDivisionError:
        return 0        

class Collector(Process):
    """Periodically collects customer happiness to a time series."""
    collect_interval = 60*10

    @Chain
    def initialize(self):
        self.stat = TSeries(storing=True, time_fnc=self.sim.clock.get, time_scale=10.0*3600)
        while True:
            self.stat.collect(100.0 * (compute_abandoned()))
            yield self.collect_interval

def main_collection():
    colors = ("red", "green", "blue", "yellow", "black")
    plotter = Plotter()
    for n in (22,):
        print "n =", n
        CallCenterSim.total_agents = n
        sim = CallCenterSim("callcenter")
        sim.stack.trace = False
        sim["collector"] = Collector()
        
        axes = plotter.add_axes()
        for run in xrange(5):
            sim.single_run(10*3600) # 10 hour
            sim["collector"].stat.run_chart(axes=axes, color=colors[run])
            pcnt_abandoned = compute_abandoned()
            print "\trun %d, abandoned = %.2f%%, total = %i, served = %i, answered = %i, predicted = %i, idle_agents = %i, p_adjust = %i" % (run, 100.0 * pcnt_abandoned, Call.calls_total, Call.calls_served, Call.calls_answered, Call.predicted_calls, Call.idle_agents, Call.predict_adjust)
        axes.set_title("%d lines and staff" % (n,))
        axes.set_xlabel("Time (days)")
        axes.set_ylabel("Abandoned calls (%)")
        axes.set_ylim(0, 100)
        plotter.update()
        
        print '---'
        print "\trun Summary:, abandoned = %.2f%%, total = %i, served = %i, answered = %i, predicted = %i, idle_agents = %i" % (100.0 * pcnt_abandoned, Call.calls_total, Call.calls_served, Call.calls_answered, Call.predicted_calls, Call.idle_agents)

if __name__ == "__main__":
    main_collection()