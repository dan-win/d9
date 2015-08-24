import unittest
import dctr as dc


class TestSolver(unittest.TestCase):
    def setUp(self):
        e = dc.PIEnvironment(
            ctr_integral_gain = 0.05,
            ctr_proportional_gain = 2.0,
            predict_adjust = 150.0,

            uptime_threshold = 5 * 60, # 5 minutes
            calls_threshold = 10,
            min_idle_agents = 3,

            target_abandon_calls = 2.5 / 100, # %
            max_abandon_calls = 3.0 /100, # %
            # set default values:

            #~ total_agents = 0,
            idle_agents = 100,

            calls_total = 0, # all outbound calls
            calls_answered = 0, # served + abandoned
            #~ calls_congested = 0, # rejected calls due to network overload
            calls_served = 0, # call processed by agents

            uptime = 0, # uptime in seconds
            interval = 1 # interval from last call in seconds
        )
        self.e = e
        self.solver = dc.PIController(e)
    
    def test_uptime_below_threshold(self):
        e = self.e
        e.uptime_threshold = 600 # seconds
        e.uptime = 300
        e.calls_total = 1000
        e.idle_agents = 100
        prediction = self.solver.predict_outgoing_calls()
        self.assertEqual(prediction, e.idle_agents)


    def test_calls_below_threshold(self):
        e = self.e
        e.calls_threshold = 600 #
        e.calls_answered = 300
        e.idle_agents = 100
        prediction = self.solver.predict_outgoing_calls()
        self.assertEqual(prediction, e.idle_agents)

    def test_max_abandon_calls(self):
        e = self.e
        e.calls_threshold = 0 #
        e.uptime_threshold = 0 #

        e.uptime = 600
        e.calls_answered = 1000
        e.calls_served = 1
        e.idle_agents = 100
        prediction = self.solver.predict_outgoing_calls()
        self.assertEqual(prediction, e.idle_agents)

    def test_predict_adjust_min(self):
        e = self.e
        e.calls_threshold = 0 #
        e.uptime_threshold = 0 #

        e.uptime = 600
        e.calls_answered = 1000
        e.calls_served = 1000
        e.idle_agents = 100
        e.predict_adjust = 0
        prediction = self.solver.predict_outgoing_calls()
        self.assertEqual(prediction, e.idle_agents)

    def test_predict_adjust_max(self):
        e = self.e
        e.calls_threshold = 0 #
        e.uptime_threshold = 0 #

        e.uptime = 600
        e.calls_answered = 1000
        e.calls_served = 1000
        e.idle_agents = 100
        e.predict_adjust = 1000
        prediction = self.solver.predict_outgoing_calls()
        self.assertEqual(prediction, e.idle_agents)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSolver)
    unittest.TextTestRunner(verbosity=2).run(suite)
