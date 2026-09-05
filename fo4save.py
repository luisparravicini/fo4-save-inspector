#!/usr/bin/env python3
"""Inspect character information in a Fallout 4 / Fallout 4 VR save.

The parser is read-only and has no third-party dependencies.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
import sys
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


MAGIC = b"FO4_SAVEGAME"
PLAYER_ACHR = 0x14
ACHR_TYPE_INDEX = 1

SPECIAL_IDS = {
    0x2C2: "strength", 0x2C3: "perception", 0x2C4: "endurance",
    0x2C5: "charisma", 0x2C6: "intelligence", 0x2C7: "agility", 0x2C8: "luck",
}

RANKED_PERKS = {
    "Action Boy/Girl", "Armorer", "Black Widow", "Blacksmith", "Bloody Mess",
    "Cap Collector", "Commando", "Demolition Expert", "Gun Nut", "Gunslinger",
    "Hacker", "Heavy Gunner", "Local Leader", "Locksmith", "Lone Wanderer",
    "Medic", "Mister Sandman", "Ninja", "Nuclear Physicist", "Pickpocket",
    "Quick Hands", "Rifleman", "Robotics Expert", "Science!", "Scrapper",
    "Scrounger", "Sneak", "Sniper", "Steady Aim", "Strong Back", "Toughness",
}

MAGAZINE_PERK_PREFIXES = {
    "Astoundingly Awesome", "Covert Operations", "Grognak the Barbarian",
    "Guns and Bullets", "Junktown Vendor", "Live & Love",
    "Massachusetts Surgical Journal", "Tesla Science", "Tumblers Today",
    "Unstoppables", "Wasteland Survival", "Islander's Almanac", "SCAV!",
}

CATEGORY_ORDER = {
    "level_up": 0, "magazine": 1, "bobblehead": 2, "companion": 3, "other": 4,
}

DLC_LABELS = {
    "DLCRobot.esm": "Automatron",
    "DLCworkshop01.esm": "Wasteland Workshop",
    "DLCCoast.esm": "Far Harbor",
    "DLCworkshop02.esm": "Contraptions Workshop",
    "DLCworkshop03.esm": "Vault-Tec Workshop",
    "DLCNukaWorld.esm": "Nuka-World",
}

COMPANION_PERK_NAMES = {
    0x001F4187: "Trigger Rush (Cait affinity perk)",
    0x001EB99B: "Robot Sympathy (Codsworth affinity perk)",
    0x001E67BC: "Combat Medic (Curie affinity perk)",
    0x0008428D: "Know Your Enemy (Danse affinity perk)",
    0x0008530E: "Cloak & Dagger (Deacon affinity perk)",
    0x00178D57: "Isodoped (Hancock affinity perk)",
    0x00178D50: "Killshot (MacCready affinity perk)",
    0x001E67BD: "Close to Metal (Nick Valentine affinity perk)",
    0x00178D54: "Gift of Gab (Piper affinity perk)",
    0x00084298: "United We Stand (Preston Garvey affinity perk)",
    0x00084290: "Berserk (Strong affinity perk)",
    0x000842A0: "Shield Harmonics (X6-88 affinity perk)",
}

PLUGIN_PERK_NAMES = {
    ("DLCNukaWorld.esm", 0x0346F9): "Smart Grenade (hidden)",
    ("DLCNukaWorld.esm", 0x035E71): "Lucky Rabbit's Foot",
    ("DLCCoast.esm", 0x018621): "Hunter's Wisdom (Old Longfellow affinity perk)",
    ("DLCNukaWorld.esm", 0x0479EF): "Lessons in Blood (Porter Gage affinity perk)",
    ("DLCCoast.esm", 0x02C9B3): "Protector of Acadia",
    ("DLCCoast.esm", 0x02C9B5): "Far Harbor Survivalist",
    ("DLCCoast.esm", 0x034E80): "Action Boy/Girl 3",
    ("DLCCoast.esm", 0x0423A3): "Strong Back 5",
    ("DLCCoast.esm", 0x04B98F): "Acadia barter perk (hidden)",
    ("DLCCoast.esm", 0x050B32): "Islander's Almanac 1",
    ("DLCCoast.esm", 0x050B33): "Islander's Almanac 2",
    ("DLCCoast.esm", 0x050B34): "Islander's Almanac 3",
    ("DLCCoast.esm", 0x050B36): "Islander's Almanac 5",
    ("DLCNukaWorld.esm", 0x02A9F8): "SCAV! - Villainous Virtuosity",
    ("DLCNukaWorld.esm", 0x02A9F9): "SCAV! - Bladed Bravado",
    ("DLCNukaWorld.esm", 0x02A9FA): "SCAV! - Pugilistic Propensities",
    ("DLCNukaWorld.esm", 0x02A9FB): "SCAV! - Cautionary Crafts",
    ("DLCNukaWorld.esm", 0x032ADF): "Shock collar perk (hidden)",
}

HIDDEN_PERK_NAMES = {
    "Acadia barter perk (hidden)", "Ashes quest perk (hidden)",
    "Common legendary modifier (hidden)", "Eleanor friendship perk (hidden)",
    "General Atomics prices perk (hidden)", "Mod armor penetration (hidden)",
    "Power armor perk (hidden)", "Power armor radiation resistance (hidden)",
    "Power armor water breathing (hidden)", "Shock collar perk (hidden)",
    "Smart Grenade (hidden)", "Tutorial drink water (hidden)",
    "Workshop player perk (hidden)",
}

# Labels are cosmetic. Unknown DLC/mod perks are still extracted with their
# plugin, local FormID, and rank, and can be named with --names.
PERK_NAMES = {
    0x0000084B: "Workshop player perk (hidden)",
    0x0001F8A9: "Power armor perk (hidden)",
    0x000221FC: "Quick Hands 1", 0x000264D8: "Blacksmith 3",
    0x0004A09F: "Gunslinger 1", 0x0004A0A9: "Gunslinger 2",
    0x0004A0AA: "Gunslinger 3", 0x0006FA1E: "Gunslinger 4", 0x00065E24: "Gunslinger 5",
    0x0004A0B6: "Rifleman 1", 0x0004A0B7: "Rifleman 2",
    0x0004A0B8: "Rifleman 3", 0x0006FA20: "Rifleman 4", 0x00065E52: "Rifleman 5",
    0x0004A0BB: "Bloody Mess 1", 0x001D2453: "Bloody Mess 2",
    0x001D2454: "Bloody Mess 3", 0x001F418E: "Bloody Mess 4",
    0x0004B258: "Mister Sandman 1", 0x001D2490: "Mister Sandman 2",
    0x001D2491: "Mister Sandman 3",
    0x0004C92A: "Sniper 1", 0x0004C92B: "Sniper 2", 0x0004C92C: "Sniper 3",
    0x0004C935: "Sneak 1", 0x000B9882: "Sneak 2", 0x000B9883: "Sneak 3",
    0x000B9884: "Sneak 4", 0x000B9881: "Sneak 5",
    0x0004D88D: "Local Leader 1", 0x001D2468: "Local Leader 2",
    0x0004D8A6: "Ninja 1", 0x000E3704: "Ninja 2", 0x000E3705: "Ninja 3",
    0x000523FF: "Locksmith 1", 0x00052400: "Locksmith 2",
    0x00052401: "Locksmith 3", 0x001D246A: "Locksmith 4",
    0x0004A0DA: "Gun Nut 1", 0x0004A0DB: "Gun Nut 2",
    0x0004A0DC: "Gun Nut 3", 0x0016578E: "Gun Nut 4",
    0x000264D9: "Science! 1", 0x000264DA: "Science! 2",
    0x000264DB: "Science! 3", 0x0016578F: "Science! 4",
    0x001D246B: "Lone Wanderer 1", 0x001D246D: "Lone Wanderer 2",
    0x001D246E: "Lone Wanderer 3",
    0x0004A0AB: "Toughness 1", 0x0004A0B0: "Scrounger 1",
    0x0004A0C5: "Commando 1", 0x0004A0C6: "Commando 2",
    0x0004A0C7: "Commando 3", 0x0006FA24: "Commando 4",
    0x00065E0D: "Commando 5", 0x0004A0D4: "Black Widow 1",
    0x00065E31: "Black Widow 2", 0x0004A0D6: "Heavy Gunner 1",
    0x0004B24E: "Strong Back 1", 0x00065E5B: "Strong Back 2",
    0x00065E5C: "Strong Back 3", 0x001D2489: "Strong Back 4",
    0x0004B253: "Blacksmith 1", 0x0004B26A: "Blacksmith 2",
    0x0004B254: "Armorer 1", 0x0004B255: "Armorer 2",
    0x0004B256: "Armorer 3", 0x001797EA: "Armorer 4",
    0x0004C923: "Demolition Expert 1", 0x0004C924: "Demolition Expert 2",
    0x0004C926: "Medic 1", 0x0004C942: "Fortune Finder 1",
    0x0004D869: "Action Boy/Girl 1", 0x0004D872: "Action Boy/Girl 1",
    0x00065DF6: "Action Boy/Girl 2", 0x0004D889: "Robotics Expert 1",
    0x00065E64: "Robotics Expert 2", 0x001ACF96: "Robotics Expert 3",
    0x0004D88A: "Pickpocket 1", 0x00052403: "Hacker 1",
    0x00052404: "Hacker 2", 0x00052405: "Hacker 3",
    0x00065E65: "Scrapper 1", 0x001D2483: "Scrapper 2",
    0x001ACF9A: "Scrounger 2", 0x001D2456: "Cap Collector 1",
    0x001D246F: "Nuclear Physicist 1", 0x001D2470: "Nuclear Physicist 2",
    0x001D2471: "Nuclear Physicist 3", 0x001D2478: "Quick Hands 2",
    0x001D2487: "Steady Aim 1", 0x001D2488: "Steady Aim 2",
    0x000E36F9: "Aquaboy/Aquagirl 1", 0x000E9453: "Aquaboy/Aquagirl 1",
    0x000F3C1A: "Lover's Embrace", 0x0005C526: "Well Rested",
    0x0006167D: "Big Guns bobblehead", 0x0006167E: "Energy Weapons bobblehead",
    0x00061681: "Medicine bobblehead", 0x00061683: "Repair bobblehead",
    0x00061687: "Speech bobblehead",
    0x0006167C: "Barter bobblehead", 0x00061680: "Lock Picking bobblehead",
    0x00061682: "Melee bobblehead", 0x00061684: "Science bobblehead",
    0x00061685: "Small Guns bobblehead", 0x00061686: "Sneak bobblehead",
    0x00061688: "Unarmed bobblehead",
    0x0008E3A6: "Grognak the Barbarian", 0x0008E3A4: "Covert Operations",
    0x0008E3A5: "Massachusetts Surgical Journal",
    0x00092A82: "Guns and Bullets", 0x00092A6E: "Tesla Science",
    0x000913C1: "Junktown Vendor", 0x000913C2: "Tumblers Today",
    0x00135F02: "Unstoppables", 0x00178D54: "Gift of Gab",
    0x0016968A: "Astoundingly Awesome 7", 0x0016968C: "Astoundingly Awesome 4",
    0x0016968E: "Astoundingly Awesome 9", 0x001E3CE6: "Astoundingly Awesome 2",
    0x001696AC: "Live & Love 5", 0x001696AE: "Live & Love 7",
    0x001C63E8: "Wasteland Survival 5", 0x001C63E9: "Wasteland Survival 7",
    0x001C63EB: "Wasteland Survival 8",
    0x00169688: "Astoundingly Awesome 6", 0x00169689: "Astoundingly Awesome 14",
    0x00169690: "Astoundingly Awesome 8", 0x00169691: "Astoundingly Awesome 3",
    0x00169695: "Astoundingly Awesome 5", 0x00169696: "Astoundingly Awesome 13",
    0x00169698: "Astoundingly Awesome 10", 0x001C501E: "Astoundingly Awesome 1",
    0x001696A8: "Live & Love 1", 0x001696A9: "Live & Love 2",
    0x001696AA: "Live & Love 3", 0x001696AB: "Live & Love 4",
    0x001696AF: "Live & Love 8", 0x00135F08: "Wasteland Survival 9",
    0x001C63E3: "Wasteland Survival 2", 0x001C63E4: "Wasteland Survival 6",
    0x001C63E6: "Wasteland Survival 1", 0x001C63E7: "Wasteland Survival 3",
    0x000B6F63: "La Coiffe",
    0x000D00A0: "Friend of The Cats", 0x000E5276: "General Atomics prices perk (hidden)",
    0x001A54A4: "Tutorial drink water (hidden)",
    0x001BE752: "Power armor water breathing (hidden)",
    0x001E6849: "Common legendary modifier (hidden)",
    0x001F4166: "Mod armor penetration (hidden)",
    0x00204A55: "Power armor radiation resistance (hidden)",
    0x00206182: "Eleanor friendship perk (hidden)",
    0x00249E2F: "Ashes quest perk (hidden)",
}

PERK_NAMES.update(COMPANION_PERK_NAMES)


def _add_special_rank_names() -> None:
    groups = {
        "Strength": [0xD9784, 0xD9785, 0xD9786, 0xD9787, 0xD9788,
                     0x11C7DB, 0x11C7DC, 0x11C7DD, 0x11C7DE],
        "Perception": [0xD9789, 0xD978A, 0xD978B, 0xD978C, 0xD978D,
                       0x11C7D7, 0x11C7D8, 0x11C7D9, 0x11C7DA],
        "Endurance": [0xD978E, 0xD978F, 0xD9790, 0xD9791, 0xD9792,
                      0x11C7CB, 0x11C7CC, 0x11C7CD, 0x11C7CE],
        "Charisma": [0xD9793, 0xD9794, 0xD9795, 0xD9796, 0xD9797,
                     0x11C7C7, 0x11C7C8, 0x11C7C9, 0x11C7CA],
        "Intelligence": [0xD9798, 0xD9799, 0xD979A, 0xD979B, 0xD979C,
                         0x11C7CF, 0x11C7D0, 0x11C7D1, 0x11C7D2],
        "Agility": [0xD979D, 0xD979E, 0xD979F, 0xD97A0, 0xD97A1,
                    0x11C7C3, 0x11C7C4, 0x11C7C5, 0x11C7C6],
        "Luck": [0xD97A2, 0xD97A3, 0xD97A4, 0xD97A5, 0xD97A6,
                 0x11C7D3, 0x11C7D4, 0x11C7D5, 0x11C7D6],
    }
    for stat, ids in groups.items():
        for rank, form_id in enumerate(ids, 2):
            PERK_NAMES[form_id] = f"{stat} Rank {rank}"


_add_special_rank_names()


class ParseError(ValueError):
    pass


class Reader:
    def __init__(self, data: bytes, pos: int = 0):
        self.data, self.pos = data, pos

    def take(self, size: int) -> bytes:
        end = self.pos + size
        if size < 0 or end > len(self.data):
            raise ParseError(f"unexpected end of file at 0x{self.pos:X}")
        value, self.pos = self.data[self.pos:end], end
        return value

    def unpack(self, fmt: str) -> Any:
        return struct.unpack(fmt, self.take(struct.calcsize(fmt)))[0]

    def u8(self) -> int: return self.unpack("<B")
    def u16(self) -> int: return self.unpack("<H")
    def u32(self) -> int: return self.unpack("<I")
    def u64(self) -> int: return self.unpack("<Q")
    def f32(self) -> float: return self.unpack("<f")

    def wstring(self) -> str:
        return self.take(self.u16()).decode("utf-8", "replace")


def read_vs(data: bytes, pos: int) -> tuple[int, int]:
    if pos >= len(data):
        raise ParseError("missing variable-size value")
    size = 1 if data[pos] & 3 == 0 else 2 if data[pos] & 3 == 1 else 3
    if pos + size > len(data):
        raise ParseError("truncated variable-size value")
    return int.from_bytes(data[pos:pos + size], "little") >> 2, pos + size


class CharacterSave:
    """The subset of a save needed to resolve the player actor."""

    def __init__(self, path: Path):
        self.path = path
        self.data = path.read_bytes()
        self.header: dict[str, Any] = {}
        self.plugins: list[str] = []
        self.form_ids: tuple[int, ...] = ()
        self.player_body = b""
        self._parse()

    def _parse(self) -> None:
        r = Reader(self.data)
        if r.take(12) != MAGIC:
            raise ParseError("not a Fallout 4 save (FO4_SAVEGAME signature missing)")
        header_size, header_start = r.u32(), r.pos
        engine_version, save_number = r.u32(), r.u32()
        name, level = r.wstring(), r.u32()
        location, play_time, race = r.wstring(), r.wstring(), r.wstring()
        gender, current_xp, required_xp = r.u16(), r.f32(), r.f32()
        filetime, width, height = r.u64(), r.u32(), r.u32()
        r.pos = header_start + header_size
        self.header = {
            "engine_version": engine_version, "save_number": save_number,
            "name": name, "level": level, "location": location,
            "play_time": play_time, "race": race,
            "gender": "female" if gender == 1 else "male" if gender == 0 else str(gender),
            "current_xp": current_xp, "required_xp": required_xp,
            "saved_at": self._filetime(filetime),
        }
        r.take(width * height * 4)
        self.header["form_version"] = r.u8()
        self.header["game_version"] = r.wstring()

        plugin_size, plugin_start = r.u32(), r.pos
        self.plugins = [r.wstring() for _ in range(r.u8())]
        r.pos = plugin_start + plugin_size

        fields = [r.u32() for _ in range(10)]
        form_id_offset, change_forms_offset, change_form_count = fields[0], fields[4], fields[9]
        form_count = struct.unpack_from("<I", self.data, form_id_offset)[0]
        form_end = form_id_offset + 4 + form_count * 4
        if form_end > len(self.data):
            raise ParseError("truncated FormID array")
        self.form_ids = struct.unpack_from(f"<{form_count}I", self.data, form_id_offset + 4)
        self.player_body = self._find_player_body(change_forms_offset, change_form_count)

    def _find_player_body(self, offset: int, count: int) -> bytes:
        r = Reader(self.data, offset)
        for _ in range(count):
            raw_ref = int.from_bytes(r.take(3), "big")
            r.u32()
            type_byte = r.u8()
            r.u8()
            length_type = type_byte >> 6
            read_len = r.u8 if length_type == 0 else r.u16 if length_type == 1 else r.u32
            stored_size, inflated_size = read_len(), read_len()
            body = r.take(stored_size)
            if type_byte & 0x3F == ACHR_TYPE_INDEX and self.resolve_ref(raw_ref) == PLAYER_ACHR:
                if inflated_size:
                    try:
                        body = zlib.decompress(body)
                    except zlib.error as exc:
                        raise ParseError(f"cannot decompress the player record: {exc}") from exc
                    if len(body) != inflated_size:
                        raise ParseError("the player record has the wrong inflated size")
                return body
        raise ParseError("player ACHR 00000014 was not found")

    def resolve_ref(self, raw: int) -> int | None:
        kind, value = raw >> 22, raw & 0x3FFFFF
        if value == 0:
            return 0
        if kind == 1:
            return value
        if kind == 2:
            return 0xFF000000 | value
        if kind == 0 and value <= len(self.form_ids):
            return self.form_ids[value - 1]
        return None

    def plugin_for(self, form_id: int) -> str:
        index = form_id >> 24
        if index == 0xFF:
            return "<created>"
        return self.plugins[index] if index < len(self.plugins) else f"<load-order {index:02X}>"

    @staticmethod
    def _filetime(value: int) -> str:
        try:
            date = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=value / 10)
            return date.isoformat()
        except (OverflowError, ValueError):
            return str(value)


def scan_actor_values(save: CharacterSave) -> tuple[dict[int, float], dict[int, tuple[float, float, float]]]:
    body, wanted = save.player_body, set(SPECIAL_IDS)
    candidates: list[tuple[int, dict[int, float], int]] = []
    for start in range(len(body)):
        try:
            count, pos = read_vs(body, start)
        except ParseError:
            continue
        if not 7 <= count <= 512 or pos + count * 7 > len(body):
            continue
        values: dict[int, float] = {}
        for _ in range(count):
            form_id = save.resolve_ref(int.from_bytes(body[pos:pos + 3], "big"))
            value = struct.unpack_from("<f", body, pos + 3)[0]
            pos += 7
            if form_id is None or not math.isfinite(value) or abs(value) > 1e12:
                values = {}
                break
            values[form_id] = value
        if wanted <= values.keys() and all(-100 <= values[x] <= 100 for x in wanted):
            candidates.append((len(values), values, pos))
    if not candidates:
        raise ParseError("could not locate the player's ActorValueStorage")
    _, base, pos = max(candidates, key=lambda item: item[0])

    modifiers: dict[int, tuple[float, float, float]] = {}
    try:
        count, pos = read_vs(body, pos)
        if count <= 512 and pos + count * 15 <= len(body):
            for _ in range(count):
                form_id = save.resolve_ref(int.from_bytes(body[pos:pos + 3], "big"))
                values = struct.unpack_from("<fff", body, pos + 3)
                pos += 15
                if form_id is not None and all(math.isfinite(x) for x in values):
                    modifiers[form_id] = values
    except (ParseError, struct.error):
        pass
    return base, modifiers


def scan_perks(save: CharacterSave, names: dict[int, str]) -> list[dict[str, Any]]:
    body = save.player_body
    candidates: list[tuple[int, list[dict[str, Any]]]] = []
    for start in range(len(body)):
        try:
            count, pos = read_vs(body, start)
        except ParseError:
            continue
        if not 1 <= count <= 1000 or pos + count * 4 > len(body):
            continue
        entries: list[dict[str, Any]] = []
        known = direct = 0
        for _ in range(count):
            raw = int.from_bytes(body[pos:pos + 3], "big")
            rank, form_id = body[pos + 3], save.resolve_ref(raw)
            pos += 4
            if form_id in (None, 0) or rank > 20:
                entries = []
                break
            plugin = save.plugin_for(form_id)
            name = names.get(form_id) or PLUGIN_PERK_NAMES.get((plugin, form_id & 0xFFFFFF))
            known += name is not None
            direct += raw >> 22 == 1
            entries.append({
                "name": name, "rank": rank,
                "form_id": f"{form_id:08X}", "local_form_id": f"{form_id & 0xFFFFFF:06X}",
                "plugin": plugin,
            })
        small_direct_array = count >= 2 and known >= 1 and direct == count
        if entries and (known >= 2 or (count >= 5 and direct >= count // 2)
                        or small_direct_array):
            candidates.append((known * 100 + direct * 2 + min(count, 200), entries))
    if not candidates:
        raise ParseError("could not locate the player's perk array")
    return max(candidates, key=lambda item: item[0])[1]


def load_names(path: Path | None) -> dict[int, str]:
    names = dict(PERK_NAMES)
    if path:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ParseError("--names must contain a JSON object")
        for key, value in raw.items():
            names[int(key, 16)] = str(value)
    return names


def clean_number(value: float) -> int | float:
    return int(value) if value.is_integer() else round(value, 6)


def make_character_perks(entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Turn engine perk records into player-facing character-sheet entries."""
    perks: dict[str, dict[str, Any]] = {}
    unidentified: list[dict[str, Any]] = []
    special_names = {name.title() for name in SPECIAL_IDS.values()}

    for entry in entries:
        name = entry["name"]
        if not name:
            unidentified.append({
                "plugin": entry["plugin"],
                "local_form_id": entry["local_form_id"],
                "rank": entry["rank"],
                "dlc": DLC_LABELS.get(entry["plugin"]),
            })
            continue
        if name in HIDDEN_PERK_NAMES:
            continue

        match = re.fullmatch(r"(.+) Rank (\d+)", name)
        if match and match.group(1) in special_names:
            continue  # Internal records already represented by the SPECIAL section.

        match = re.fullmatch(r"(.+) (\d+)", name)
        if match and match.group(1) in RANKED_PERKS:
            label, rank = match.group(1), int(match.group(2))
        else:
            label, rank = name, entry["rank"]

        previous = perks.get(label)
        if previous is None or rank > previous["rank"]:
            perks[label] = {
                "name": label,
                "rank": rank,
                "category": perk_category(label),
                "dlc": DLC_LABELS.get(entry["plugin"]),
            }

    result = sorted(
        perks.values(),
        key=lambda perk: (CATEGORY_ORDER[perk["category"]], perk["name"].casefold()),
    )
    return result, unidentified


def perk_category(name: str) -> str:
    if name in RANKED_PERKS:
        return "level_up"
    if any(name == prefix or name.startswith(prefix + " ") for prefix in MAGAZINE_PERK_PREFIXES):
        return "magazine"
    if name.casefold().endswith(" bobblehead"):
        return "bobblehead"
    if name.endswith(" affinity perk)"):
        return "companion"
    return "other"


def extract_character(save: CharacterSave, names: dict[int, str]) -> dict[str, Any]:
    base_values, modifiers = scan_actor_values(save)
    special: dict[str, Any] = {}
    for form_id, label in SPECIAL_IDS.items():
        base = base_values[form_id]
        permanent, temporary, damage = modifiers.get(form_id, (0.0, 0.0, 0.0))
        special[label] = {
            "base": clean_number(base),
            "permanent_modifier": clean_number(permanent),
            "temporary_modifier": clean_number(temporary),
            "damage_modifier": clean_number(damage),
            "current": clean_number(base + permanent + temporary + damage),
        }
    stored_perks = scan_perks(save, names)
    perks, unidentified = make_character_perks(stored_perks)
    return {
        **save.header,
        "special": special,
        "perks": perks,
        "unidentified_perks": unidentified,
        "stored_perk_entry_count": len(stored_perks),
    }


def print_character(info: dict[str, Any]) -> None:
    print(f"Name:       {info['name']}")
    print(f"Level:      {info['level']}")
    print(f"Gender:     {info['gender']}")
    print(f"Race:       {info['race']}")
    print(f"Location:   {info['location']}")
    print(f"Play time:  {info['play_time']}")
    print(f"XP:         {info['current_xp']:.3f} / {info['required_xp']:.3f}")
    print("\nSPECIAL:")
    for name, value in info["special"].items():
        modifiers = value["current"] - value["base"]
        suffix = f" (base {value['base']}, modifiers {modifiers:+})" if modifiers else ""
        print(f"  {name.title():12} {value['current']}{suffix}")
    headings = {
        "level_up": "Level-up perks",
        "magazine": "Magazine perks",
        "bobblehead": "Bobbleheads",
        "companion": "Companion perks",
        "other": "Other perks",
    }
    current_category = None
    for perk in info["perks"]:
        if perk["category"] != current_category:
            current_category = perk["category"]
            print(f"\n{headings[current_category]}:")
        suffix = f" — rank {perk['rank']}" if perk["rank"] > 1 else ""
        dlc = f" [{perk['dlc']}]" if perk["dlc"] else ""
        print(f"  {perk['name']}{dlc}{suffix}")
    if info["unidentified_perks"]:
        print("\nUnidentified perks:")
        for perk in info["unidentified_perks"]:
            suffix = f" — rank {perk['rank']}" if perk["rank"] > 1 else ""
            dlc = f" [{perk['dlc']}]" if perk["dlc"] else ""
            print(f"  {perk['plugin']}:{perk['local_form_id']}{dlc}{suffix}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("save", type=Path, help="Fallout 4/VR .fos save")
    parser.add_argument("--names", type=Path,
                        help="JSON object mapping resolved 8-digit FormIDs to friendly names")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)
    try:
        info = extract_character(CharacterSave(args.save), load_names(args.names))
        print(json.dumps(info, indent=2)) if args.json else print_character(info)
        return 0
    except (OSError, ParseError, ValueError, json.JSONDecodeError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
