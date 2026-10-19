from app.analytics.engine import Analytics


def compare_submarkets(store, args):
    result = Analytics(store).query(
        args.model_copy(update={"operation": "rank", "review_status": "APPROVED"})
    )
    result["warnings"] = [
        "Only rows sharing definition, publisher, source series, period and unit can receive a rank. No geography averages are computed."
    ]
    return result


def analyse_submarket(store, args):
    return Analytics(store).query(args.model_copy(update={"operation": "trend"}))
