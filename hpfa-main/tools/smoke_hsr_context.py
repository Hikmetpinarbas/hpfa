from hpfa.security.hsr_context import validate_context

def run():
    ok = True
    try:
        validate_context({
            "event_start_time":1.0,"prev_event_time":1.0,
            "state_id":"CONTROLLED","prev_state_id":"DEAD_BALL",
            "possession_effect":"START","event_type":"PASS"
        })
    except Exception as e:
        print("FAIL:", e); ok=False
    print("PASS" if ok else "FAIL")

if __name__=="__main__": run()
