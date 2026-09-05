import unittest

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


class PerkArrayTests(unittest.TestCase):
    def test_small_early_game_perk_array(self):
        save = SyntheticSave([
            (0x1A54A4, 1),
            (0x00084B, 1),
        ])

        perks = fo4save.scan_perks(save, fo4save.load_names(None))

        self.assertEqual(["001A54A4", "0000084B"],
                         [perk["form_id"] for perk in perks])


if __name__ == "__main__":
    unittest.main()
