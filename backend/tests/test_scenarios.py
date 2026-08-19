import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from app.models import Observation, Scenario, ScenarioEvent, ScenarioImport, ScenarioUpdate
from app.scenarios import ScenarioStore, optimize_scenario, parse_scenario
from app.state import AppStateStore


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

    def test_scenario_update_and_delete(self):
        with TemporaryDirectory() as directory:
            store = ScenarioStore(str(Path(directory) / "test.db"))
            created = store.import_scenario(ScenarioImport(name="v1", content="one"))
            updated = store.update(created.id, ScenarioUpdate(name="v2", content="two"))
            self.assertEqual(updated.revision, 2)
            self.assertTrue(store.delete(created.id))
            self.assertIsNone(store.get(created.id))

    def test_observation_history(self):
        with TemporaryDirectory() as directory:
            store = AppStateStore(str(Path(directory) / "test.db"))
            record = store.add_observation(Observation(source="test", kind="signal", value={"ok": True}))
            self.assertEqual(store.list_observations()[0].id, record.id)


if __name__ == "__main__":
    unittest.main()
