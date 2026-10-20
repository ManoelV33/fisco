"""Uso: python3 montar.py plano.json  — plano: {tid: {"dir": ..., "itens": [[n, sec, legenda], ...]}}
Gera figsel/<tid>/ e funde as posições em figuras.json."""
import sys, json, subprocess, os
plano = json.load(open(sys.argv[1]))
sel = {t: {"dir": p["dir"], "ids": [i[0] for i in p["itens"]]} for t, p in plano.items()}
json.dump(sel, open("/tmp/claude-0/-home-claude/34318a0f-9386-53df-abf6-c40c8ce7ba0a/scratchpad/sel.json", "w"))
subprocess.run(["python3", "figsel.py", "/tmp/claude-0/-home-claude/34318a0f-9386-53df-abf6-c40c8ce7ba0a/scratchpad/sel.json"], check=True)
fig = json.load(open("figuras.json")) if os.path.exists("figuras.json") else {}
for t, p in plano.items():
    lst = json.load(open(f"figsel/{t}/figs.json"))
    fig[t] = [{"sec": sec, "img": lst[k]["id"], "legenda": leg, "mapa": lst[k]["secao"] == "mapa"} for k, (n, sec, leg) in enumerate(p["itens"])]
json.dump(fig, open("figuras.json", "w"), ensure_ascii=False, indent=1)
print({t: len(v) for t, v in fig.items()})
