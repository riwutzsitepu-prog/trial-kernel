from pathlib import Path

import re

p = Path("kernel/kernel/cgroup/cpuset.c")
s = p.read_text()
if "#ifdef CONFIG_CPUSET_ASSIST\nstatic ssize_t cpuset_write_resmask_assist" not in s:
    pattern = re.compile(
        r"(static ssize_t cpuset_write_resmask_assist\(.*?\n\})\n\n"
        r"(?=static ssize_t cpuset_write_resmask_wrapper)",
        re.S,
    )
    m = pattern.search(s)
    if not m:
        raise SystemExit("cpuset assist function not found")
    wrapped = "#ifdef CONFIG_CPUSET_ASSIST\n" + m.group(1) + "\n#endif\n\n"
    s = s[:m.start()] + wrapped + s[m.end():]
    p.write_text(s)

p = Path("kernel/kernel/sched/tune.c")
s = p.read_text()
marker = """#endif

static struct cftype files[] = {"""
repl = """#endif

#ifndef CONFIG_STUNE_ASSIST
#define boost_write_wrapper boost_write
#define prefer_idle_write_wrapper prefer_idle_write
#endif

static struct cftype files[] = {"""
if "#define boost_write_wrapper boost_write" not in s:
    if marker not in s:
        raise SystemExit("schedtune wrapper anchor not found")
    p.write_text(s.replace(marker, repl, 1))

fixed = []
source_root = Path("kernel")
for hp in source_root.rglob("*.h"):
    try:
        hs = hp.read_text()
    except UnicodeDecodeError:
        continue
    if "#include <trace/define_trace.h>" not in hs:
        continue
    lines = hs.splitlines()
    changed = False
    rel_parent = hp.relative_to(source_root).parent.as_posix()
    replacement = "#define TRACE_INCLUDE_PATH ../../" + rel_parent
    for i, line in enumerate(lines):
        if line.strip() == "#define TRACE_INCLUDE_PATH .":
            lines[i] = replacement
            changed = True
    if changed:
        hp.write_text("\n".join(lines) + ("\n" if hs.endswith("\n") else ""))
        fixed.append(str(hp))
print("trace include paths fixed:", len(fixed))

names = ("btfm_slim.h", "btfm_slim_wcn3990.h", "device_event.h")
changed = 0
for root in (Path("kernel/drivers/bluetooth"), Path("kernel/sound/soc/msm")):
    for src in list(root.rglob("*.c")) + list(root.rglob("*.h")):
        text = src.read_text(errors="ignore")
        newtext = text
        for name in names:
            newtext = newtext.replace(f"#include <{name}>", f'#include "{name}"')
        if newtext != text:
            src.write_text(newtext)
            changed += 1
print("local-header fixes:", changed)
