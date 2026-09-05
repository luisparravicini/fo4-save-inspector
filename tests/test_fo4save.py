import io
import unittest
from contextlib import redirect_stdout

import fo4save


class SyntheticSave:
    def __init__(self, entries):
        encoded = bytearray([len(entries) << 2])
        for form_id, rank in entries:
            raw_ref = (1 << 22) | form_id
            encoded.extend(raw_ref.to_bytes(3, "big"))
            encoded.append(rank)
        self.player_body = bytes(encoded)

    @staticmethod
    def resolve_ref(raw):
        return raw & 0x3FFFFF if raw >> 22 == 1 else None

    @staticmethod
    def plugin_for(form_id):
        return "Fallout4.esm"

    local_form_id = staticmethod(fo4save.CharacterSave.local_form_id)


class PerkArrayTests(unittest.TestCase):
    def test_small_early_game_perk_array(self):
        save = SyntheticSave([
            (0x1A54A4, 1),
            (0x00084B, 1),
        ])

        perks = fo4save.scan_perks(save, fo4save.load_names(None))

        self.assertEqual(["001A54A4", "0000084B"],
                         [perk["form_id"] for perk in perks])

    def test_known_hidden_perks_are_omitted(self):
        entries = [
            {"name": "Tutorial drink water (hidden)", "rank": 1,
             "form_id": "001A54A4", "local_form_id": "1A54A4",
             "plugin": "Fallout4.esm"},
        ]

        perks, unidentified = fo4save.make_character_perks(entries)

        self.assertEqual([], perks)
        self.assertEqual([], unidentified)

    def test_new_ranked_and_magazine_names_are_classified(self):
        entries = [
            {"name": "Commando 1", "rank": 1, "form_id": "0004A0C5",
             "local_form_id": "04A0C5", "plugin": "Fallout4.esm"},
            {"name": "Commando 3", "rank": 1, "form_id": "0004A0C7",
             "local_form_id": "04A0C7", "plugin": "Fallout4.esm"},
            {"name": "Islander's Almanac 2", "rank": 1,
             "form_id": "03050B33", "local_form_id": "050B33",
             "plugin": "DLCCoast.esm"},
        ]

        perks, _ = fo4save.make_character_perks(entries)

        self.assertEqual("Commando", perks[0]["name"])
        self.assertEqual(3, perks[0]["rank"])
        self.assertEqual("level_up", perks[0]["category"])
        self.assertEqual("magazine", perks[1]["category"])

    def test_quest_rewards_are_classified(self):
        entries = [
            {"name": "Protector of Acadia", "rank": 1,
             "form_id": "0302C9B3", "local_form_id": "02C9B3",
             "plugin": "DLCCoast.esm"},
        ]

        perks, _ = fo4save.make_character_perks(entries)

        self.assertEqual("quest", perks[0]["category"])


class LightPluginTests(unittest.TestCase):
    def setUp(self):
        self.save = fo4save.CharacterSave.__new__(fo4save.CharacterSave)
        self.save.plugins = ["Fallout4.esm"]
        self.save.light_plugins = ["First.esl", "Second.esl"]

    def test_light_plugin_index_is_resolved(self):
        self.assertEqual("Second.esl", self.save.plugin_for(0xFE001ABC))

    def test_light_plugin_local_form_id_uses_twelve_bits(self):
        self.assertEqual("ABC", self.save.local_form_id(0xFE001ABC))

    def test_unknown_light_plugin_index_is_explicit(self):
        self.assertEqual("<light-load-order 002>",
                         self.save.plugin_for(0xFE002123))


class OutputTests(unittest.TestCase):
    def test_rank_separator_is_valid_unicode(self):
        info = {
            "name": "Test", "level": 2, "gender": "male", "race": "HumanRace",
            "location": "Commonwealth", "play_time": "0d.1h.0m",
            "current_xp": 0.0, "required_xp": 200.0,
            "special": {},
            "perks": [{"name": "Commando", "rank": 2,
                       "category": "level_up", "dlc": None}],
            "unidentified_perks": [],
        }
        output = io.StringIO()

        with redirect_stdout(output):
            fo4save.print_character(info)

        self.assertIn("Commando — rank 2", output.getvalue())
        self.assertNotIn("\N{REPLACEMENT CHARACTER}", output.getvalue())


if __name__ == "__main__":
    unittest.main()
