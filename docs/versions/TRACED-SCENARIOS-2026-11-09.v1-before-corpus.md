# Scenarios with rendered traces (2026-11-09)

Every scenario below has a trace at `data/store/traces/<scenario id>/trace.json` (readable copy of the record: `trace.yaml`;
the messages the model sees are in `trace.json`). The scenario itself (F, Q, A) is the path in the table.

**What a "family" is here:** one source document (one DOE OHA decision, one OGE regulation example, one incident).
Within a family, `extract` rows are distinct decisions pulled from that source; `restyle`, `flip` and `add_fact` rows are
perturbations of an extracted one (restyle = same answer, new surface; flip = a fact changed so the answer changes;
add_fact = an extra fact). So most multi-scenario families here are one or two real decisions plus their perturbations.
Families with more than one distinct `extract` decision are marked **multi-decision**.

✓ = in grid A1 (the 100 X1s now running).

236 traced scenarios in 72 families.

## personnel security adjudication (105 scenarios, 38 families)

### OHA-26-0020 (4)

| | scenario | kind | scenario file |
|---|---|---|---|
| ✓ | `DR-OHA-26-0020-addfact1@v1` | add_fact | `data/store/scenarios/OHA-26-0020/DR-OHA-26-0020-addfact1@v1.yaml` |
| ✓ | `DR-OHA-26-0020-flip1@v1` | flip | `data/store/scenarios/OHA-26-0020/DR-OHA-26-0020-flip1@v1.yaml` |
| ✓ | `DR-OHA-26-0020-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0020/DR-OHA-26-0020-restyle1@v1.yaml` |
| ✓ | `DR-OHA-26-0020@v1` | extract | `data/store/scenarios/OHA-26-0020/DR-OHA-26-0020@v1.yaml` |

### OHA-26-0022 (4)

| | scenario | kind | scenario file |
|---|---|---|---|
| ✓ | `DR-OHA-26-0022-addfact1@v1` | add_fact | `data/store/scenarios/OHA-26-0022/DR-OHA-26-0022-addfact1@v1.yaml` |
| ✓ | `DR-OHA-26-0022-flip1@v1` | flip | `data/store/scenarios/OHA-26-0022/DR-OHA-26-0022-flip1@v1.yaml` |
| ✓ | `DR-OHA-26-0022-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0022/DR-OHA-26-0022-restyle1@v1.yaml` |
| ✓ | `DR-OHA-26-0022@v1` | extract | `data/store/scenarios/OHA-26-0022/DR-OHA-26-0022@v1.yaml` |

### OHA-26-0029 (4)

| | scenario | kind | scenario file |
|---|---|---|---|
| ✓ | `DR-OHA-26-0029-addfact1@v1` | add_fact | `data/store/scenarios/OHA-26-0029/DR-OHA-26-0029-addfact1@v1.yaml` |
| ✓ | `DR-OHA-26-0029-flip1@v1` | flip | `data/store/scenarios/OHA-26-0029/DR-OHA-26-0029-flip1@v1.yaml` |
| ✓ | `DR-OHA-26-0029-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0029/DR-OHA-26-0029-restyle1@v1.yaml` |
| ✓ | `DR-OHA-26-0029@v1` | extract | `data/store/scenarios/OHA-26-0029/DR-OHA-26-0029@v1.yaml` |

### OHA-26-0062 (4)

| | scenario | kind | scenario file |
|---|---|---|---|
| ✓ | `DR-OHA-26-0062-addfact1@v1` | add_fact | `data/store/scenarios/OHA-26-0062/DR-OHA-26-0062-addfact1@v1.yaml` |
| ✓ | `DR-OHA-26-0062-flip1@v1` | flip | `data/store/scenarios/OHA-26-0062/DR-OHA-26-0062-flip1@v1.yaml` |
| ✓ | `DR-OHA-26-0062-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0062/DR-OHA-26-0062-restyle1@v1.yaml` |
| ✓ | `DR-OHA-26-0062@v1` | extract | `data/store/scenarios/OHA-26-0062/DR-OHA-26-0062@v1.yaml` |

### OHA-26-0086 (4)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0086-addfact1@v1` | add_fact | `data/store/scenarios/OHA-26-0086/DR-OHA-26-0086-addfact1@v1.yaml` |
|  | `DR-OHA-26-0086-flip1@v1` | flip | `data/store/scenarios/OHA-26-0086/DR-OHA-26-0086-flip1@v1.yaml` |
|  | `DR-OHA-26-0086-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0086/DR-OHA-26-0086-restyle1@v1.yaml` |
|  | `DR-OHA-26-0086@v1` | extract | `data/store/scenarios/OHA-26-0086/DR-OHA-26-0086@v1.yaml` |

### OHA-26-0088 (4)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0088-addfact1@v1` | add_fact | `data/store/scenarios/OHA-26-0088/DR-OHA-26-0088-addfact1@v1.yaml` |
|  | `DR-OHA-26-0088-flip1@v1` | flip | `data/store/scenarios/OHA-26-0088/DR-OHA-26-0088-flip1@v1.yaml` |
|  | `DR-OHA-26-0088-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0088/DR-OHA-26-0088-restyle1@v1.yaml` |
|  | `DR-OHA-26-0088@v1` | extract | `data/store/scenarios/OHA-26-0088/DR-OHA-26-0088@v1.yaml` |

### OHA-26-0090 (4)

| | scenario | kind | scenario file |
|---|---|---|---|
| ✓ | `DR-OHA-26-0090-addfact1@v1` | add_fact | `data/store/scenarios/OHA-26-0090/DR-OHA-26-0090-addfact1@v1.yaml` |
| ✓ | `DR-OHA-26-0090-flip1@v1` | flip | `data/store/scenarios/OHA-26-0090/DR-OHA-26-0090-flip1@v1.yaml` |
| ✓ | `DR-OHA-26-0090-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0090/DR-OHA-26-0090-restyle1@v1.yaml` |
| ✓ | `DR-OHA-26-0090@v1` | extract | `data/store/scenarios/OHA-26-0090/DR-OHA-26-0090@v1.yaml` |

### OHA-26-0100 (4)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0100-2@v1` | extract | `data/store/scenarios/OHA-26-0100/DR-OHA-26-0100-2@v1.yaml` |
|  | `DR-OHA-26-0100-addfact2@v1` | add_fact | `data/store/scenarios/OHA-26-0100/DR-OHA-26-0100-addfact2@v1.yaml` |
|  | `DR-OHA-26-0100-flip3@v1` | flip | `data/store/scenarios/OHA-26-0100/DR-OHA-26-0100-flip3@v1.yaml` |
|  | `DR-OHA-26-0100-restyle3@v1` | restyle | `data/store/scenarios/OHA-26-0100/DR-OHA-26-0100-restyle3@v1.yaml` |

### OHA-26-0118 (4)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0118-addfact1@v1` | add_fact | `data/store/scenarios/OHA-26-0118/DR-OHA-26-0118-addfact1@v1.yaml` |
|  | `DR-OHA-26-0118-flip1@v1` | flip | `data/store/scenarios/OHA-26-0118/DR-OHA-26-0118-flip1@v1.yaml` |
|  | `DR-OHA-26-0118-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0118/DR-OHA-26-0118-restyle1@v1.yaml` |
|  | `DR-OHA-26-0118@v1` | extract | `data/store/scenarios/OHA-26-0118/DR-OHA-26-0118@v1.yaml` |

### OHA-26-0144 (4)

| | scenario | kind | scenario file |
|---|---|---|---|
| ✓ | `DR-OHA-26-0144-addfact1@v1` | add_fact | `data/store/scenarios/OHA-26-0144/DR-OHA-26-0144-addfact1@v1.yaml` |
| ✓ | `DR-OHA-26-0144-flip1@v1` | flip | `data/store/scenarios/OHA-26-0144/DR-OHA-26-0144-flip1@v1.yaml` |
| ✓ | `DR-OHA-26-0144-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0144/DR-OHA-26-0144-restyle1@v1.yaml` |
| ✓ | `DR-OHA-26-0144@v1` | extract | `data/store/scenarios/OHA-26-0144/DR-OHA-26-0144@v1.yaml` |

### OHA-25-0123 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-25-0123-addfact1@v1` | add_fact | `data/store/scenarios/OHA-25-0123/DR-OHA-25-0123-addfact1@v1.yaml` |
|  | `DR-OHA-25-0123-restyle1@v1` | restyle | `data/store/scenarios/OHA-25-0123/DR-OHA-25-0123-restyle1@v1.yaml` |
|  | `DR-OHA-25-0123@v1` | extract | `data/store/scenarios/OHA-25-0123/DR-OHA-25-0123@v1.yaml` |

### OHA-26-0011 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0011-addfact1@v1` | add_fact | `data/store/scenarios/OHA-26-0011/DR-OHA-26-0011-addfact1@v1.yaml` |
|  | `DR-OHA-26-0011-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0011/DR-OHA-26-0011-restyle1@v1.yaml` |
|  | `DR-OHA-26-0011@v1` | extract | `data/store/scenarios/OHA-26-0011/DR-OHA-26-0011@v1.yaml` |

### OHA-26-0016 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0016-addfact1@v1` | add_fact | `data/store/scenarios/OHA-26-0016/DR-OHA-26-0016-addfact1@v1.yaml` |
|  | `DR-OHA-26-0016-flip1@v1` | flip | `data/store/scenarios/OHA-26-0016/DR-OHA-26-0016-flip1@v1.yaml` |
|  | `DR-OHA-26-0016-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0016/DR-OHA-26-0016-restyle1@v1.yaml` |

### OHA-26-0017 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0017-flip1@v1` | flip | `data/store/scenarios/OHA-26-0017/DR-OHA-26-0017-flip1@v1.yaml` |
|  | `DR-OHA-26-0017-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0017/DR-OHA-26-0017-restyle1@v1.yaml` |
|  | `DR-OHA-26-0017@v1` | extract | `data/store/scenarios/OHA-26-0017/DR-OHA-26-0017@v1.yaml` |

### OHA-26-0035 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0035-flip1@v1` | flip | `data/store/scenarios/OHA-26-0035/DR-OHA-26-0035-flip1@v1.yaml` |
|  | `DR-OHA-26-0035-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0035/DR-OHA-26-0035-restyle1@v1.yaml` |
|  | `DR-OHA-26-0035@v1` | extract | `data/store/scenarios/OHA-26-0035/DR-OHA-26-0035@v1.yaml` |

### OHA-26-0051 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0051-addfact1@v1` | add_fact | `data/store/scenarios/OHA-26-0051/DR-OHA-26-0051-addfact1@v1.yaml` |
|  | `DR-OHA-26-0051-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0051/DR-OHA-26-0051-restyle1@v1.yaml` |
|  | `DR-OHA-26-0051@v1` | extract | `data/store/scenarios/OHA-26-0051/DR-OHA-26-0051@v1.yaml` |

### OHA-26-0069 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0069-addfact1@v1` | add_fact | `data/store/scenarios/OHA-26-0069/DR-OHA-26-0069-addfact1@v1.yaml` |
|  | `DR-OHA-26-0069-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0069/DR-OHA-26-0069-restyle1@v1.yaml` |
|  | `DR-OHA-26-0069@v1` | extract | `data/store/scenarios/OHA-26-0069/DR-OHA-26-0069@v1.yaml` |

### OHA-26-0085 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0085-addfact1@v1` | add_fact | `data/store/scenarios/OHA-26-0085/DR-OHA-26-0085-addfact1@v1.yaml` |
|  | `DR-OHA-26-0085-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0085/DR-OHA-26-0085-restyle1@v1.yaml` |
|  | `DR-OHA-26-0085@v1` | extract | `data/store/scenarios/OHA-26-0085/DR-OHA-26-0085@v1.yaml` |

### OHA-26-0089 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0089-addfact1@v1` | add_fact | `data/store/scenarios/OHA-26-0089/DR-OHA-26-0089-addfact1@v1.yaml` |
|  | `DR-OHA-26-0089-flip1@v1` | flip | `data/store/scenarios/OHA-26-0089/DR-OHA-26-0089-flip1@v1.yaml` |
|  | `DR-OHA-26-0089-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0089/DR-OHA-26-0089-restyle1@v1.yaml` |

### OHA-26-0101 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0101-flip1@v1` | flip | `data/store/scenarios/OHA-26-0101/DR-OHA-26-0101-flip1@v1.yaml` |
|  | `DR-OHA-26-0101-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0101/DR-OHA-26-0101-restyle1@v1.yaml` |
|  | `DR-OHA-26-0101@v1` | extract | `data/store/scenarios/OHA-26-0101/DR-OHA-26-0101@v1.yaml` |

### OHA-26-0110 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0110-flip1@v1` | flip | `data/store/scenarios/OHA-26-0110/DR-OHA-26-0110-flip1@v1.yaml` |
|  | `DR-OHA-26-0110-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0110/DR-OHA-26-0110-restyle1@v1.yaml` |
|  | `DR-OHA-26-0110@v1` | extract | `data/store/scenarios/OHA-26-0110/DR-OHA-26-0110@v1.yaml` |

### OHA-26-0122 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0122-addfact2@v1` | add_fact | `data/store/scenarios/OHA-26-0122/DR-OHA-26-0122-addfact2@v1.yaml` |
|  | `DR-OHA-26-0122-restyle2@v1` | restyle | `data/store/scenarios/OHA-26-0122/DR-OHA-26-0122-restyle2@v1.yaml` |
|  | `DR-OHA-26-0122@v1` | extract | `data/store/scenarios/OHA-26-0122/DR-OHA-26-0122@v1.yaml` |

### OHA-26-0145 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0145-flip1@v1` | flip | `data/store/scenarios/OHA-26-0145/DR-OHA-26-0145-flip1@v1.yaml` |
|  | `DR-OHA-26-0145-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0145/DR-OHA-26-0145-restyle1@v1.yaml` |
|  | `DR-OHA-26-0145@v1` | extract | `data/store/scenarios/OHA-26-0145/DR-OHA-26-0145@v1.yaml` |

### OHA-26-0005 (2)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0005-flip1@v1` | flip | `data/store/scenarios/OHA-26-0005/DR-OHA-26-0005-flip1@v1.yaml` |
|  | `DR-OHA-26-0005-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0005/DR-OHA-26-0005-restyle1@v1.yaml` |

### OHA-26-0008 (2)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0008-flip1@v1` | flip | `data/store/scenarios/OHA-26-0008/DR-OHA-26-0008-flip1@v1.yaml` |
|  | `DR-OHA-26-0008-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0008/DR-OHA-26-0008-restyle1@v1.yaml` |

### OHA-26-0012 (2)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0012-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0012/DR-OHA-26-0012-restyle1@v1.yaml` |
|  | `DR-OHA-26-0012@v1` | extract | `data/store/scenarios/OHA-26-0012/DR-OHA-26-0012@v1.yaml` |

### OHA-26-0038 (2)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0038-flip1@v1` | flip | `data/store/scenarios/OHA-26-0038/DR-OHA-26-0038-flip1@v1.yaml` |
|  | `DR-OHA-26-0038@v1` | extract | `data/store/scenarios/OHA-26-0038/DR-OHA-26-0038@v1.yaml` |

### OHA-26-0047 (2)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0047-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0047/DR-OHA-26-0047-restyle1@v1.yaml` |
|  | `DR-OHA-26-0047@v1` | extract | `data/store/scenarios/OHA-26-0047/DR-OHA-26-0047@v1.yaml` |

### OHA-26-0052 (2)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0052-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0052/DR-OHA-26-0052-restyle1@v1.yaml` |
|  | `DR-OHA-26-0052@v1` | extract | `data/store/scenarios/OHA-26-0052/DR-OHA-26-0052@v1.yaml` |

### OHA-26-0055 (2)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0055-flip1@v1` | flip | `data/store/scenarios/OHA-26-0055/DR-OHA-26-0055-flip1@v1.yaml` |
|  | `DR-OHA-26-0055@v1` | extract | `data/store/scenarios/OHA-26-0055/DR-OHA-26-0055@v1.yaml` |

### OHA-26-0074 (2)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0074-addfact1@v1` | add_fact | `data/store/scenarios/OHA-26-0074/DR-OHA-26-0074-addfact1@v1.yaml` |
|  | `DR-OHA-26-0074-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0074/DR-OHA-26-0074-restyle1@v1.yaml` |

### OHA-26-0106 (2)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0106-flip1@v1` | flip | `data/store/scenarios/OHA-26-0106/DR-OHA-26-0106-flip1@v1.yaml` |
|  | `DR-OHA-26-0106-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0106/DR-OHA-26-0106-restyle1@v1.yaml` |

### OHA-26-0108 (2)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0108-flip1@v1` | flip | `data/store/scenarios/OHA-26-0108/DR-OHA-26-0108-flip1@v1.yaml` |
|  | `DR-OHA-26-0108-restyle1@v1` | restyle | `data/store/scenarios/OHA-26-0108/DR-OHA-26-0108-restyle1@v1.yaml` |

### OHA-26-0123 (2)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OHA-26-0123-flip1@v1` | flip | `data/store/scenarios/OHA-26-0123/DR-OHA-26-0123-flip1@v1.yaml` |
|  | `DR-OHA-26-0123@v1` | extract | `data/store/scenarios/OHA-26-0123/DR-OHA-26-0123@v1.yaml` |

- `OHA-26-0024`: `DR-OHA-26-0024-flip1@v1` (flip) — `data/store/scenarios/OHA-26-0024/DR-OHA-26-0024-flip1@v1.yaml`
- `OHA-26-0044`: `DR-OHA-26-0044@v1` (extract) — `data/store/scenarios/OHA-26-0044/DR-OHA-26-0044@v1.yaml`
- `OHA-26-0087`: `DR-OHA-26-0087-2@v1` (extract) — `data/store/scenarios/OHA-26-0087/DR-OHA-26-0087-2@v1.yaml`
- `OHA-26-0163`: `DR-OHA-26-0163@v1` (extract) — `data/store/scenarios/OHA-26-0163/DR-OHA-26-0163@v1.yaml`

## federal employee gifts and ethics (69 scenarios, 17 families)

### OGE-2635-702 (8) — **multi-decision** (2 extracted)

| | scenario | kind | scenario file |
|---|---|---|---|
| ✓ | `DR-OGE-2635-702-1@v1` | extract | `data/store/scenarios/OGE-2635-702/DR-OGE-2635-702-1@v1.yaml` |
| ✓ | `DR-OGE-2635-702-2@v1` | extract | `data/store/scenarios/OGE-2635-702/DR-OGE-2635-702-2@v1.yaml` |
| ✓ | `DR-OGE-2635-702-addfact1@v1` | add_fact | `data/store/scenarios/OGE-2635-702/DR-OGE-2635-702-addfact1@v1.yaml` |
| ✓ | `DR-OGE-2635-702-addfact2@v1` | add_fact | `data/store/scenarios/OGE-2635-702/DR-OGE-2635-702-addfact2@v1.yaml` |
| ✓ | `DR-OGE-2635-702-flip1@v1` | flip | `data/store/scenarios/OGE-2635-702/DR-OGE-2635-702-flip1@v1.yaml` |
| ✓ | `DR-OGE-2635-702-flip2@v1` | flip | `data/store/scenarios/OGE-2635-702/DR-OGE-2635-702-flip2@v1.yaml` |
| ✓ | `DR-OGE-2635-702-restyle1@v1` | restyle | `data/store/scenarios/OGE-2635-702/DR-OGE-2635-702-restyle1@v1.yaml` |
| ✓ | `DR-OGE-2635-702-restyle2@v1` | restyle | `data/store/scenarios/OGE-2635-702/DR-OGE-2635-702-restyle2@v1.yaml` |

### OGE-2635-808 (7) — **multi-decision** (2 extracted)

| | scenario | kind | scenario file |
|---|---|---|---|
| ✓ | `DR-OGE-2635-808-1@v1` | extract | `data/store/scenarios/OGE-2635-808/DR-OGE-2635-808-1@v1.yaml` |
| ✓ | `DR-OGE-2635-808-2@v1` | extract | `data/store/scenarios/OGE-2635-808/DR-OGE-2635-808-2@v1.yaml` |
| ✓ | `DR-OGE-2635-808-addfact1@v1` | add_fact | `data/store/scenarios/OGE-2635-808/DR-OGE-2635-808-addfact1@v1.yaml` |
| ✓ | `DR-OGE-2635-808-addfact2@v1` | add_fact | `data/store/scenarios/OGE-2635-808/DR-OGE-2635-808-addfact2@v1.yaml` |
| ✓ | `DR-OGE-2635-808-flip1@v1` | flip | `data/store/scenarios/OGE-2635-808/DR-OGE-2635-808-flip1@v1.yaml` |
| ✓ | `DR-OGE-2635-808-restyle1@v1` | restyle | `data/store/scenarios/OGE-2635-808/DR-OGE-2635-808-restyle1@v1.yaml` |
| ✓ | `DR-OGE-2635-808-restyle2@v1` | restyle | `data/store/scenarios/OGE-2635-808/DR-OGE-2635-808-restyle2@v1.yaml` |

### OGE-2635-304 (6)

| | scenario | kind | scenario file |
|---|---|---|---|
| ✓ | `DR-OGE-2635-304-1@v1` | extract | `data/store/scenarios/OGE-2635-304/DR-OGE-2635-304-1@v1.yaml` |
| ✓ | `DR-OGE-2635-304-addfact1@v1` | add_fact | `data/store/scenarios/OGE-2635-304/DR-OGE-2635-304-addfact1@v1.yaml` |
| ✓ | `DR-OGE-2635-304-addfact2@v1` | add_fact | `data/store/scenarios/OGE-2635-304/DR-OGE-2635-304-addfact2@v1.yaml` |
| ✓ | `DR-OGE-2635-304-flip1@v1` | flip | `data/store/scenarios/OGE-2635-304/DR-OGE-2635-304-flip1@v1.yaml` |
| ✓ | `DR-OGE-2635-304-restyle1@v1` | restyle | `data/store/scenarios/OGE-2635-304/DR-OGE-2635-304-restyle1@v1.yaml` |
| ✓ | `DR-OGE-2635-304-restyle2@v1` | restyle | `data/store/scenarios/OGE-2635-304/DR-OGE-2635-304-restyle2@v1.yaml` |

### OGE-2635-502 (6) — **multi-decision** (2 extracted)

| | scenario | kind | scenario file |
|---|---|---|---|
| ✓ | `DR-OGE-2635-502-1@v1` | extract | `data/store/scenarios/OGE-2635-502/DR-OGE-2635-502-1@v1.yaml` |
| ✓ | `DR-OGE-2635-502-2@v1` | extract | `data/store/scenarios/OGE-2635-502/DR-OGE-2635-502-2@v1.yaml` |
| ✓ | `DR-OGE-2635-502-addfact1@v1` | add_fact | `data/store/scenarios/OGE-2635-502/DR-OGE-2635-502-addfact1@v1.yaml` |
| ✓ | `DR-OGE-2635-502-flip1@v1` | flip | `data/store/scenarios/OGE-2635-502/DR-OGE-2635-502-flip1@v1.yaml` |
| ✓ | `DR-OGE-2635-502-restyle1@v1` | restyle | `data/store/scenarios/OGE-2635-502/DR-OGE-2635-502-restyle1@v1.yaml` |
| ✓ | `DR-OGE-2635-502-restyle2@v1` | restyle | `data/store/scenarios/OGE-2635-502/DR-OGE-2635-502-restyle2@v1.yaml` |

### OGE-2635-807 (6) — **multi-decision** (2 extracted)

| | scenario | kind | scenario file |
|---|---|---|---|
| ✓ | `DR-OGE-2635-807-1@v1` | extract | `data/store/scenarios/OGE-2635-807/DR-OGE-2635-807-1@v1.yaml` |
| ✓ | `DR-OGE-2635-807-2@v1` | extract | `data/store/scenarios/OGE-2635-807/DR-OGE-2635-807-2@v1.yaml` |
| ✓ | `DR-OGE-2635-807-addfact1@v1` | add_fact | `data/store/scenarios/OGE-2635-807/DR-OGE-2635-807-addfact1@v1.yaml` |
| ✓ | `DR-OGE-2635-807-flip1@v1` | flip | `data/store/scenarios/OGE-2635-807/DR-OGE-2635-807-flip1@v1.yaml` |
| ✓ | `DR-OGE-2635-807-restyle1@v1` | restyle | `data/store/scenarios/OGE-2635-807/DR-OGE-2635-807-restyle1@v1.yaml` |
| ✓ | `DR-OGE-2635-807-restyle2@v1` | restyle | `data/store/scenarios/OGE-2635-807/DR-OGE-2635-807-restyle2@v1.yaml` |

### OGE-2635-302 (4)

| | scenario | kind | scenario file |
|---|---|---|---|
| ✓ | `DR-OGE-2635-302-addfact1@v1` | add_fact | `data/store/scenarios/OGE-2635-302/DR-OGE-2635-302-addfact1@v1.yaml` |
| ✓ | `DR-OGE-2635-302-flip1@v1` | flip | `data/store/scenarios/OGE-2635-302/DR-OGE-2635-302-flip1@v1.yaml` |
| ✓ | `DR-OGE-2635-302-restyle1@v1` | restyle | `data/store/scenarios/OGE-2635-302/DR-OGE-2635-302-restyle1@v1.yaml` |
| ✓ | `DR-OGE-2635-302@v1` | extract | `data/store/scenarios/OGE-2635-302/DR-OGE-2635-302@v1.yaml` |

### OGE-2635-403 (4)

| | scenario | kind | scenario file |
|---|---|---|---|
| ✓ | `DR-OGE-2635-403-addfact1@v1` | add_fact | `data/store/scenarios/OGE-2635-403/DR-OGE-2635-403-addfact1@v1.yaml` |
| ✓ | `DR-OGE-2635-403-flip1@v1` | flip | `data/store/scenarios/OGE-2635-403/DR-OGE-2635-403-flip1@v1.yaml` |
| ✓ | `DR-OGE-2635-403-restyle1@v1` | restyle | `data/store/scenarios/OGE-2635-403/DR-OGE-2635-403-restyle1@v1.yaml` |
| ✓ | `DR-OGE-2635-403@v1` | extract | `data/store/scenarios/OGE-2635-403/DR-OGE-2635-403@v1.yaml` |

### OGE-2635-503 (4)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OGE-2635-503-addfact1@v1` | add_fact | `data/store/scenarios/OGE-2635-503/DR-OGE-2635-503-addfact1@v1.yaml` |
|  | `DR-OGE-2635-503-flip1@v1` | flip | `data/store/scenarios/OGE-2635-503/DR-OGE-2635-503-flip1@v1.yaml` |
|  | `DR-OGE-2635-503-restyle1@v1` | restyle | `data/store/scenarios/OGE-2635-503/DR-OGE-2635-503-restyle1@v1.yaml` |
|  | `DR-OGE-2635-503@v1` | extract | `data/store/scenarios/OGE-2635-503/DR-OGE-2635-503@v1.yaml` |

### OGE-2635-206 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OGE-2635-206-flip1@v1` | flip | `data/store/scenarios/OGE-2635-206/DR-OGE-2635-206-flip1@v1.yaml` |
|  | `DR-OGE-2635-206-restyle1@v1` | restyle | `data/store/scenarios/OGE-2635-206/DR-OGE-2635-206-restyle1@v1.yaml` |
|  | `DR-OGE-2635-206@v1` | extract | `data/store/scenarios/OGE-2635-206/DR-OGE-2635-206@v1.yaml` |

### OGE-2635-402 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OGE-2635-402-flip1@v1` | flip | `data/store/scenarios/OGE-2635-402/DR-OGE-2635-402-flip1@v1.yaml` |
|  | `DR-OGE-2635-402-restyle1@v1` | restyle | `data/store/scenarios/OGE-2635-402/DR-OGE-2635-402-restyle1@v1.yaml` |
|  | `DR-OGE-2635-402@v1` | extract | `data/store/scenarios/OGE-2635-402/DR-OGE-2635-402@v1.yaml` |

### OGE-2635-603 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OGE-2635-603-flip1@v1` | flip | `data/store/scenarios/OGE-2635-603/DR-OGE-2635-603-flip1@v1.yaml` |
|  | `DR-OGE-2635-603-restyle1@v1` | restyle | `data/store/scenarios/OGE-2635-603/DR-OGE-2635-603-restyle1@v1.yaml` |
|  | `DR-OGE-2635-603@v1` | extract | `data/store/scenarios/OGE-2635-603/DR-OGE-2635-603@v1.yaml` |

### OGE-2635-606 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OGE-2635-606-addfact1@v1` | add_fact | `data/store/scenarios/OGE-2635-606/DR-OGE-2635-606-addfact1@v1.yaml` |
|  | `DR-OGE-2635-606-flip1@v1` | flip | `data/store/scenarios/OGE-2635-606/DR-OGE-2635-606-flip1@v1.yaml` |
|  | `DR-OGE-2635-606-restyle1@v1` | restyle | `data/store/scenarios/OGE-2635-606/DR-OGE-2635-606-restyle1@v1.yaml` |

### OGE-2635-704 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OGE-2635-704-addfact1@v1` | add_fact | `data/store/scenarios/OGE-2635-704/DR-OGE-2635-704-addfact1@v1.yaml` |
|  | `DR-OGE-2635-704-flip1@v1` | flip | `data/store/scenarios/OGE-2635-704/DR-OGE-2635-704-flip1@v1.yaml` |
|  | `DR-OGE-2635-704-restyle1@v1` | restyle | `data/store/scenarios/OGE-2635-704/DR-OGE-2635-704-restyle1@v1.yaml` |

### OGE-2635-705 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OGE-2635-705-addfact1@v1` | add_fact | `data/store/scenarios/OGE-2635-705/DR-OGE-2635-705-addfact1@v1.yaml` |
|  | `DR-OGE-2635-705-restyle1@v1` | restyle | `data/store/scenarios/OGE-2635-705/DR-OGE-2635-705-restyle1@v1.yaml` |
|  | `DR-OGE-2635-705@v1` | extract | `data/store/scenarios/OGE-2635-705/DR-OGE-2635-705@v1.yaml` |

### OGE-2635-802 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OGE-2635-802-flip1@v1` | flip | `data/store/scenarios/OGE-2635-802/DR-OGE-2635-802-flip1@v1.yaml` |
|  | `DR-OGE-2635-802-restyle1@v1` | restyle | `data/store/scenarios/OGE-2635-802/DR-OGE-2635-802-restyle1@v1.yaml` |
|  | `DR-OGE-2635-802@v1` | extract | `data/store/scenarios/OGE-2635-802/DR-OGE-2635-802@v1.yaml` |

### OGE-2635-303 (2)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OGE-2635-303-flip1@v1` | flip | `data/store/scenarios/OGE-2635-303/DR-OGE-2635-303-flip1@v1.yaml` |
|  | `DR-OGE-2635-303-restyle1@v1` | restyle | `data/store/scenarios/OGE-2635-303/DR-OGE-2635-303-restyle1@v1.yaml` |

- `OGE-2635-204`: `DR-OGE-2635-204-2@v1` (extract) — `data/store/scenarios/OGE-2635-204/DR-OGE-2635-204-2@v1.yaml`

## military-operational (52 scenarios, 12 families)

### KUNDUZ-2009 (8) — **multi-decision** (3 extracted)

| | scenario | kind | scenario file |
|---|---|---|---|
| ✓ | `DR-KUNDUZ-2009-1@v1` | extract | `data/store/scenarios/KUNDUZ-2009/DR-KUNDUZ-2009-1@v1.yaml` |
| ✓ | `DR-KUNDUZ-2009-2@v1` | extract | `data/store/scenarios/KUNDUZ-2009/DR-KUNDUZ-2009-2@v1.yaml` |
| ✓ | `DR-KUNDUZ-2009-3@v1` | extract | `data/store/scenarios/KUNDUZ-2009/DR-KUNDUZ-2009-3@v1.yaml` |
| ✓ | `DR-KUNDUZ-2009-flip1@v1` | flip | `data/store/scenarios/KUNDUZ-2009/DR-KUNDUZ-2009-flip1@v1.yaml` |
| ✓ | `DR-KUNDUZ-2009-flip2@v1` | flip | `data/store/scenarios/KUNDUZ-2009/DR-KUNDUZ-2009-flip2@v1.yaml` |
| ✓ | `DR-KUNDUZ-2009-restyle1@v1` | restyle | `data/store/scenarios/KUNDUZ-2009/DR-KUNDUZ-2009-restyle1@v1.yaml` |
| ✓ | `DR-KUNDUZ-2009-restyle2@v1` | restyle | `data/store/scenarios/KUNDUZ-2009/DR-KUNDUZ-2009-restyle2@v1.yaml` |
| ✓ | `DR-KUNDUZ-2009-restyle3@v1` | restyle | `data/store/scenarios/KUNDUZ-2009/DR-KUNDUZ-2009-restyle3@v1.yaml` |

### WCK-CONVOY-2024 (7) — **multi-decision** (2 extracted)

| | scenario | kind | scenario file |
|---|---|---|---|
| ✓ | `DR-WCK-CONVOY-2024-1@v1` | extract | `data/store/scenarios/WCK-CONVOY-2024/DR-WCK-CONVOY-2024-1@v1.yaml` |
| ✓ | `DR-WCK-CONVOY-2024-2@v1` | extract | `data/store/scenarios/WCK-CONVOY-2024/DR-WCK-CONVOY-2024-2@v1.yaml` |
| ✓ | `DR-WCK-CONVOY-2024-addfact1@v1` | add_fact | `data/store/scenarios/WCK-CONVOY-2024/DR-WCK-CONVOY-2024-addfact1@v1.yaml` |
| ✓ | `DR-WCK-CONVOY-2024-flip1@v1` | flip | `data/store/scenarios/WCK-CONVOY-2024/DR-WCK-CONVOY-2024-flip1@v1.yaml` |
| ✓ | `DR-WCK-CONVOY-2024-flip2@v1` | flip | `data/store/scenarios/WCK-CONVOY-2024/DR-WCK-CONVOY-2024-flip2@v1.yaml` |
| ✓ | `DR-WCK-CONVOY-2024-restyle1@v1` | restyle | `data/store/scenarios/WCK-CONVOY-2024/DR-WCK-CONVOY-2024-restyle1@v1.yaml` |
| ✓ | `DR-WCK-CONVOY-2024-restyle2@v1` | restyle | `data/store/scenarios/WCK-CONVOY-2024/DR-WCK-CONVOY-2024-restyle2@v1.yaml` |

### ICTY-NATO-1999 (6)

| | scenario | kind | scenario file |
|---|---|---|---|
| ✓ | `DR-ICTY-NATO-1999-1@v1` | extract | `data/store/scenarios/ICTY-NATO-1999/DR-ICTY-NATO-1999-1@v1.yaml` |
| ✓ | `DR-ICTY-NATO-1999-addfact1@v1` | add_fact | `data/store/scenarios/ICTY-NATO-1999/DR-ICTY-NATO-1999-addfact1@v1.yaml` |
| ✓ | `DR-ICTY-NATO-1999-addfact2@v1` | add_fact | `data/store/scenarios/ICTY-NATO-1999/DR-ICTY-NATO-1999-addfact2@v1.yaml` |
| ✓ | `DR-ICTY-NATO-1999-flip1@v1` | flip | `data/store/scenarios/ICTY-NATO-1999/DR-ICTY-NATO-1999-flip1@v1.yaml` |
| ✓ | `DR-ICTY-NATO-1999-flip2@v1` | flip | `data/store/scenarios/ICTY-NATO-1999/DR-ICTY-NATO-1999-flip2@v1.yaml` |
| ✓ | `DR-ICTY-NATO-1999-restyle1@v1` | restyle | `data/store/scenarios/ICTY-NATO-1999/DR-ICTY-NATO-1999-restyle1@v1.yaml` |

### TARNAK-2002 (6) — **multi-decision** (2 extracted)

| | scenario | kind | scenario file |
|---|---|---|---|
| ✓ | `DR-TARNAK-2002-1@v1` | extract | `data/store/scenarios/TARNAK-2002/DR-TARNAK-2002-1@v1.yaml` |
| ✓ | `DR-TARNAK-2002-2@v1` | extract | `data/store/scenarios/TARNAK-2002/DR-TARNAK-2002-2@v1.yaml` |
| ✓ | `DR-TARNAK-2002-flip1@v1` | flip | `data/store/scenarios/TARNAK-2002/DR-TARNAK-2002-flip1@v1.yaml` |
| ✓ | `DR-TARNAK-2002-flip2@v1` | flip | `data/store/scenarios/TARNAK-2002/DR-TARNAK-2002-flip2@v1.yaml` |
| ✓ | `DR-TARNAK-2002-restyle1@v1` | restyle | `data/store/scenarios/TARNAK-2002/DR-TARNAK-2002-restyle1@v1.yaml` |
| ✓ | `DR-TARNAK-2002-restyle2@v1` | restyle | `data/store/scenarios/TARNAK-2002/DR-TARNAK-2002-restyle2@v1.yaml` |

### STARK-1987 (4)

| | scenario | kind | scenario file |
|---|---|---|---|
| ✓ | `DR-STARK-1987-1@v1` | extract | `data/store/scenarios/STARK-1987/DR-STARK-1987-1@v1.yaml` |
| ✓ | `DR-STARK-1987-addfact1@v1` | add_fact | `data/store/scenarios/STARK-1987/DR-STARK-1987-addfact1@v1.yaml` |
| ✓ | `DR-STARK-1987-flip1@v1` | flip | `data/store/scenarios/STARK-1987/DR-STARK-1987-flip1@v1.yaml` |
| ✓ | `DR-STARK-1987-restyle1@v1` | restyle | `data/store/scenarios/STARK-1987/DR-STARK-1987-restyle1@v1.yaml` |

### VINCENNES-1988 (4)

| | scenario | kind | scenario file |
|---|---|---|---|
| ✓ | `DR-VINCENNES-1988-1@v1` | extract | `data/store/scenarios/VINCENNES-1988/DR-VINCENNES-1988-1@v1.yaml` |
| ✓ | `DR-VINCENNES-1988-addfact1@v1` | add_fact | `data/store/scenarios/VINCENNES-1988/DR-VINCENNES-1988-addfact1@v1.yaml` |
| ✓ | `DR-VINCENNES-1988-flip1@v1` | flip | `data/store/scenarios/VINCENNES-1988/DR-VINCENNES-1988-flip1@v1.yaml` |
| ✓ | `DR-VINCENNES-1988-restyle1@v1` | restyle | `data/store/scenarios/VINCENNES-1988/DR-VINCENNES-1988-restyle1@v1.yaml` |

### ANACONDA-2002 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-ANACONDA-2002-1@v1` | extract | `data/store/scenarios/ANACONDA-2002/DR-ANACONDA-2002-1@v1.yaml` |
|  | `DR-ANACONDA-2002-flip1@v1` | flip | `data/store/scenarios/ANACONDA-2002/DR-ANACONDA-2002-flip1@v1.yaml` |
|  | `DR-ANACONDA-2002-restyle1@v1` | restyle | `data/store/scenarios/ANACONDA-2002/DR-ANACONDA-2002-restyle1@v1.yaml` |

### BLACKHAWK-SHOOTDOWN-1994 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-BLACKHAWK-1994-1@v1` | extract | `data/store/scenarios/BLACKHAWK-SHOOTDOWN-1994/DR-BLACKHAWK-1994-1@v1.yaml` |
|  | `DR-BLACKHAWK-SHOOTDOWN-1994-addfact1@v1` | add_fact | `data/store/scenarios/BLACKHAWK-SHOOTDOWN-1994/DR-BLACKHAWK-SHOOTDOWN-1994-addfact1@v1.yaml` |
|  | `DR-BLACKHAWK-SHOOTDOWN-1994-flip1@v1` | flip | `data/store/scenarios/BLACKHAWK-SHOOTDOWN-1994/DR-BLACKHAWK-SHOOTDOWN-1994-flip1@v1.yaml` |

### FARAH-2009 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-FARAH-2009-1@v1` | extract | `data/store/scenarios/FARAH-2009/DR-FARAH-2009-1@v1.yaml` |
|  | `DR-FARAH-2009-addfact1@v1` | add_fact | `data/store/scenarios/FARAH-2009/DR-FARAH-2009-addfact1@v1.yaml` |
|  | `DR-FARAH-2009-flip1@v1` | flip | `data/store/scenarios/FARAH-2009/DR-FARAH-2009-flip1@v1.yaml` |

### HARIM-2014 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-HARIM-2014-1@v1` | extract | `data/store/scenarios/HARIM-2014/DR-HARIM-2014-1@v1.yaml` |
|  | `DR-HARIM-2014-flip1@v1` | flip | `data/store/scenarios/HARIM-2014/DR-HARIM-2014-flip1@v1.yaml` |
|  | `DR-HARIM-2014-restyle1@v1` | restyle | `data/store/scenarios/HARIM-2014/DR-HARIM-2014-restyle1@v1.yaml` |

### MOSUL-ALJADIDA-2017 (3)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-MOSUL-ALJADIDA-2017-1@v1` | extract | `data/store/scenarios/MOSUL-ALJADIDA-2017/DR-MOSUL-ALJADIDA-2017-1@v1.yaml` |
|  | `DR-MOSUL-ALJADIDA-2017-flip1@v1` | flip | `data/store/scenarios/MOSUL-ALJADIDA-2017/DR-MOSUL-ALJADIDA-2017-flip1@v1.yaml` |
|  | `DR-MOSUL-ALJADIDA-2017-restyle1@v1` | restyle | `data/store/scenarios/MOSUL-ALJADIDA-2017/DR-MOSUL-ALJADIDA-2017-restyle1@v1.yaml` |

### ALJINAH-2017 (2)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-ALJINAH-2017-1@v1` | extract | `data/store/scenarios/ALJINAH-2017/DR-ALJINAH-2017-1@v1.yaml` |
|  | `DR-ALJINAH-2017-restyle1@v1` | restyle | `data/store/scenarios/ALJINAH-2017/DR-ALJINAH-2017-restyle1@v1.yaml` |


## maritime autonomy (2 scenarios, 1 families)

### AUT-001 (2)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-AUT-001-r1@v1` | import | `data/store/scenarios/AUT-001/DR-AUT-001-r1@v1.yaml` |
|  | `DR-AUT-001@v1` | import | `data/store/scenarios/AUT-001/DR-AUT-001@v1.yaml` |


## military intelligence oversight (2 scenarios, 1 families)

### INT-301 (2)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-INT-301-r1@v1` | import | `data/store/scenarios/INT-301/DR-INT-301-r1@v1.yaml` |
|  | `DR-INT-301@v1` | import | `data/store/scenarios/INT-301/DR-INT-301@v1.yaml` |


## oversight and records (2 scenarios, 1 families)

### OVS-301 (2)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-OVS-301-r1@v1` | import | `data/store/scenarios/OVS-301/DR-OVS-301-r1@v1.yaml` |
|  | `DR-OVS-301@v1` | import | `data/store/scenarios/OVS-301/DR-OVS-301@v1.yaml` |


## foreign disclosure to partners (2 scenarios, 1 families)

### REL-301 (2)

| | scenario | kind | scenario file |
|---|---|---|---|
|  | `DR-REL-301-r1@v1` | import | `data/store/scenarios/REL-301/DR-REL-301-r1@v1.yaml` |
|  | `DR-REL-301@v1` | import | `data/store/scenarios/REL-301/DR-REL-301@v1.yaml` |


## counterterrorism analytics (1 scenarios, 1 families)

- `INT-103`: `DR-INT-103@v1` (import) — `data/store/scenarios/INT-103/DR-INT-103@v1.yaml`

