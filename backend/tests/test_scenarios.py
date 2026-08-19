import unittest

from app.models import Scenario, ScenarioEvent
from app.scenarios import optimize_scenario, parse_scenario


class ScenarioTests(unittest.TestCase):
    def test_plain_text_becomes_narrative(self):
        events = parse_scenario("hello")
        self.assertEqual(events[0].type, "narrative")

    def test_json_events_are_validated(self):
        events = parse_scenario('{"events": [{"type": "audio", "payload": {}}]}')
        self.assertEqual(events[0].type, "audio")

    def test_optimizer_never_returns_device_commands(self):
        scenario = Scenario(name="test", source="hello", events=[ScenarioEvent(type="narrative")], created_at="now", updated_at="now")
        result = optimize_scenario(scenario)
        self.assertTrue(result.suggested_settings["require_confirmation"])
        self.assertNotIn("device_command", str(result.model_dump()))


if __name__ == "__main__":
    unittest.main()
