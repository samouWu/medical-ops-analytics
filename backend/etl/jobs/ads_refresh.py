import argparse
import json

from etl.jobs.pipeline import refresh_ads


def main():
    parser = argparse.ArgumentParser(description="按日期区间回刷ADS日/周/月指标")
    parser.add_argument("--start", help="开始日期 YYYY-MM-DD；缺省为数据最早日期")
    parser.add_argument("--end", help="结束日期 YYYY-MM-DD；缺省为数据最晚日期")
    parser.add_argument("--grains", default="day,week,month", help="逗号分隔，可选day,week,month")
    parser.add_argument("--dept-code", help="只回刷指定科室；缺省回刷全部科室和全院汇总")
    args = parser.parse_args()
    grains = tuple(item.strip() for item in args.grains.split(",") if item.strip())
    result = refresh_ads(args.start, args.end, grains, args.dept_code)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
