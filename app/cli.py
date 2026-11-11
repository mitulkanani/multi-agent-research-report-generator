import argparse
from app.models.schemas import ResearchRequest
from app.services.research import ResearchService


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a multi-agent cited research report")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--audience", default="General audience")
    parser.add_argument("--question", action="append", default=[])
    args = parser.parse_args()
    result = ResearchService().run(ResearchRequest(topic=args.topic, audience=args.audience, focus_questions=args.question))
    if result.report:
        print(result.report.markdown)
    else:
        raise SystemExit(result.error or "Research failed")


if __name__ == "__main__":
    main()
