# Fallout 4 Save Inspector

`fo4save.py` is a dependency-free, read-only Python 3.10+ inspector currently
focused on the player character in Fallout 4 and Fallout 4 VR `.fos` saves. It
extracts:

- name, level, gender, race, location, play time, and XP;
- base and modified SPECIAL values;
- character-sheet perks, with multi-tier perk records collapsed to the highest
  acquired rank.

> **Compatibility:** Tested against 52 Fallout 4 VR saves from game version
> 1.2.72.0 (save form version 67) and five desktop Fallout 4 saves from game
> versions 1.10.984.0 and 1.11.221.0 (save form versions 68 and 69). All 57
> saves parse successfully. The desktop corpus includes nine ESL plugins and
> `FE` FormIDs, which are resolved to their light-plugin names and three-digit
> local IDs. It has no acquired perks supplied by those plugins, so extraction
> of an actual ESL-defined perk has not yet been observed end to end.

Perks are grouped and alphabetized as level-up choices, magazine perks,
bobbleheads, companion affinity perks, quest perks, and other bonuses. The
built-in names cover the player-facing base-game perk chart and its official
DLC ranks, official perk magazines, skill bobbleheads, companion affinity
perks, and documented permanent quest rewards. Temporary effects, NPC
abilities, equipment modifiers, cut content, and internal bookkeeping perks
are not presented as character-sheet perks. Companion labels use the same
`Perk (Companion affinity perk)` format for the base game and DLCs. Perks
defined by an official add-on receive a secondary label such as `[Far Harbor]`
or `[Nuka-World]` without being moved out of their category.

The adjacent `.f4se` co-save is not required for these fields.

## Usage

```bash
python3 fo4save.py Quicksave0_....fos
python3 fo4save.py Quicksave0_....fos --json
```

On Windows, the Python launcher can be used instead:

```powershell
py fo4save.py Quicksave0_....fos --json
```

Use `--json` for machine-readable output. It includes the save metadata,
detailed SPECIAL values, categorized perks, unidentified perks, and stored perk
entry count. Text and JSON output are UTF-8 on Windows, Linux, and macOS. The
output can be saved to a file:

```bash
python3 fo4save.py save.fos --json > character.json
```

Internal bookkeeping perks are omitted from the character sheet. Separate
records such as `Sniper 1` and `Sniper 2` become `Sniper — rank 2`. Magazine
issue numbers are not mistaken for perk ranks, and collectible perks that use
one record with a stored rank retain that rank.

Unknown DLC and mod perk records are still detected and remain visible as
`Plugin.esm:LocalFormID`. Supply a mapping to give them friendly labels using a
JSON file whose keys are resolved eight-digit load-order FormIDs:

```json
{
  "020346F9": "Smart Grenade",
  "09001234": "My mod perk"
}
```

```bash
python3 fo4save.py save.fos --names perk-names.json
```

Resolved FormIDs depend on the save's plugin load order. A regular plugin's
high-byte prefix can therefore change between load orders. An ESL/light-plugin
FormID also contains its `FExxx` light-plugin index, so a custom mapping may
need to be updated when the load order changes.

The parser reads only enough of the save container to find the canonical
player actor (`00000014`), resolve its references, and decode its actor-value
and perk arrays. It never modifies the save.

## Limitations

The player record does not label these structures for this standalone parser,
so it locates the actor-value and perk arrays using validated structural
patterns. An unsupported or substantially different save format may therefore
fail with an explicit parsing error.

Only records stored in the player's perk array are reported. This tool is not
a catalog of every game object and does not report inventory items, temporary
effects, NPC-only abilities, or perks the character has not acquired. ESL
FormIDs and plugin names are supported, but the compatibility corpus does not
yet contain an acquired perk defined by an ESL plugin.

## Testing

Run the dependency-free unit tests with:

```bash
python3 -m unittest discover -s tests -v
```

The local compatibility pass used real Fallout 4 and Fallout 4 VR saves on
Windows. Save files, character details, machine paths, and generated output are
not part of this repository. The parser and CLI remain portable Python and use
UTF-8 output across Windows, Linux, and macOS.

## Format notes and credits

The implementation was informed by public Fallout 4 save-format research and
the open-source [FallrimTools/ReSaver] and [fo4-save-cleaner] projects. Their
source code is not included in this repository. Three-byte save RefIDs use a
one-based index into the save's four-byte FormID array.

Regular FormIDs use their high byte as an index into the full-plugin list.
Light-plugin FormIDs use `FExxxYYY`, where `xxx` indexes the save's ESL/light
plugin list and `YYY` is the plugin-local FormID.

SPECIAL is displayed as base plus the Creation Engine's permanent, temporary,
and damage modifier slots, so equipment and other active effects stay separate
from the underlying character values.

[FallrimTools/ReSaver]: https://github.com/mdfairch/FallrimTools
[fo4-save-cleaner]: https://github.com/pub-struct/fo4-save-cleaner

## License

This project is available under the [MIT License](LICENSE).

## Disclaimer

This is an unofficial fan-made project. It is not affiliated with or endorsed
by Bethesda Softworks. Fallout 4, Fallout 4 VR, and related names are the
property of their respective owners.
