# Fallout 4 VR character extractor

`fo4save.py` is a dependency-free, read-only Python 3 script focused on the
player character in Fallout 4 and Fallout 4 VR `.fos` saves. It extracts:

- name, level, gender, race, location, play time, and XP;
- base and modified SPECIAL values;
- character-sheet perks, with multi-tier perk records collapsed to the highest
  acquired rank.

The adjacent `.f4se` co-save is not required for these fields.

## Usage

```bash
python3 fo4save.py Quicksave0_....fos
python3 fo4save.py Quicksave0_....fos --json
```

Internal bookkeeping perks are omitted from the character sheet. Separate
records such as `Sniper 1` and `Sniper 2` become `Sniper — rank 2`. Magazine
issue numbers are not mistaken for perk ranks, and collectible perks that use
one record with a stored rank retain that rank.

DLC and mod perks do not require hard-coded names to be extracted: unidentified
entries remain visible as `Plugin.esm:LocalFormID`. You can supply more friendly
labels with a JSON file whose keys are resolved eight-digit load-order FormIDs:

```json
{
  "020346F9": "Smart Grenade",
  "09001234": "My mod perk"
}
```

```bash
python3 fo4save.py save.fos --names perk-names.json
```

The parser reads only enough of the save container to find the canonical
player actor (`00000014`), resolve its references, and decode its actor-value
and perk arrays. It never modifies the save.

## Format notes and credits

The implementation was informed by public Fallout 4 save-format research and
the open-source FallrimTools/ReSaver and `fo4-save-cleaner` projects. Three-byte
save RefIDs use a one-based index into the save's four-byte FormID array.

SPECIAL is displayed as base plus the Creation Engine's permanent, temporary,
and damage modifier slots, so equipment and other active effects stay separate
from the underlying character values.
