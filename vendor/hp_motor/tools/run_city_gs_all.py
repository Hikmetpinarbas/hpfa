import subprocess, sys, os

def run(cmd):
    print("\n$ " + " ".join(cmd))
    p = subprocess.run(cmd, text=True)
    if p.returncode != 0:
        raise SystemExit(p.returncode)

def main():
    # 1) core convert
    run([sys.executable, "tools/convert_city_gs_to_core.py"])

    # 2) momentum
    run([sys.executable, "tools/momentum_city_gs.py"])

    # 3) phase v3 (produces v3 csv + png)
    run([sys.executable, "tools/phase_city_gs_v3.py"])

    # 4) phase v6 (final phase shares)
    run([sys.executable, "tools/phase_city_gs_v7.py"])

    # 5) scorecard v6
    run([sys.executable, "tools/scorecard.py",
         "--phase", "artifacts/phase/city_gs_phase_5min_v7.csv",
         "--label", "phase_label_v7"])

    # 6) dashboard
    run([sys.executable, "tools/dashboard_city_gs.py"])

    print("\n[OK] City-GS full pipeline complete.")

if __name__ == "__main__":
    main()
