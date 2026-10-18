import argparse
import json
import time

from app.database import Store


def main():
    parser = argparse.ArgumentParser(description="London Office Intelligence | monitoring, reporting and research")
    parser.add_argument("command", choices=["init", "monitor", "scheduler", "report", "ask", "review", "model-check", "notify"])
    parser.add_argument("--run", choices=["morning", "evening", "once"], default="once")
    parser.add_argument("--id", help="Report or observation ID")
    parser.add_argument("--question")
    parser.add_argument("--pdf", action="store_true")
    parser.add_argument("--status", choices=["APPROVED", "REJECTED", "RETRACTED"])
    parser.add_argument("--reviewer")
    parser.add_argument("--reason")
    parser.add_argument("--loop", action="store_true", help="Run independent scheduler continuously; OS timers can instead call once per minute")
    parser.add_argument("--isolated-smtp", action="store_true", help="Send only to explicitly configured loopback capture SMTP")
    args = parser.parse_args()
    store = Store()
    result = {}
    if args.command == "init":
        from app.skills.monitor import register_sources
        from app.skills.source_reader import registry
        register_sources(store, registry())
        result = {"status": "INITIALIZED", "database": str(store.path)}
    elif args.command == "monitor":
        from app.skills.monitor import run_monitor
        result = run_monitor(store, args.run)
    elif args.command == "scheduler":
        from app.services.scheduler import tick
        while True:
            result = tick(store)
            print(json.dumps({"scheduler_runs": result}), flush=True)
            if not args.loop:
                return
            time.sleep(20)
    elif args.command == "report":
        from app.skills.report import make_report, export_pdf
        report = make_report(store)
        result = {k: v for k, v in report.items() if k != "data"}
        if args.pdf:
            result["pdf_path"] = str(export_pdf(store, report["id"]))
    elif args.command == "ask":
        from app.agent import ask
        result = ask(store, args.question or "Summarise verifiable London office market developments.")
    elif args.command == "review":
        from app.skills.monitor import review_observation
        if not all((args.id, args.status, args.reviewer, args.reason)):
            parser.error("review requires --id, --status, --reviewer and --reason")
        review_observation(store, args.id, args.status, args.reviewer, args.reason)
        result = {"status": args.status, "observation_id": args.id}
    elif args.command == "model-check":
        from app.agent import completion
        store.set_setting("model_block", None)
        try:
            response = completion(store, [{"role": "user", "content": "Reply OK only."}], max_tokens=16)
            result = {"status": "PASS", "model": response.model, "output": response.choices[0].message.content,
                      "scope": "Connectivity only; not tool-calling acceptance"}
        except ValueError as exc:
            result = {"status": "BLOCKED", "reason": str(exc)}
    elif args.command == "notify":
        from app.services.notifications import dispatch
        row = store.one("SELECT id FROM reports ORDER BY created_at DESC LIMIT 1")
        if not (args.id or row):
            parser.error("Generate a report first")
        result = {"deliveries": dispatch(store, args.id or row["id"], test=True, isolated_smtp=args.isolated_smtp)}
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
