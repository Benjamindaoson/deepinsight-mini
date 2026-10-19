from app.analytics.engine import Analytics


def query_market_metrics(store, args):
    return Analytics(store).query(args)


def compare_market_periods(store, args):
    return Analytics(store).query(args.model_copy(update={"operation": "compare"}))


def get_market_trends(store, args):
    return Analytics(store).query(args.model_copy(update={"operation": "trend"}))


def get_data_coverage(store, args):
    return Analytics(store).query(args.model_copy(update={"operation": "coverage", "review_status": "ALL"}))
