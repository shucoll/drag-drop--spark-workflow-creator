from flask import Flask, request, render_template_string, Response
from pyspark.sql import SparkSession
import pandas as pd
import os
import json
 
app = Flask(__name__)
final_output_data = []
 
def execute_pipeline(pipeline_json):
    spark = SparkSession.builder.master("local[*]").appName("NodeRED Pipeline").getOrCreate()
    sc = spark.sparkContext
    rdd_map = {}
    active_rdd = None
    headers = []
 
    for step in pipeline_json.get("pipeline", []):
        operation = step.get("operation")
        print("operation", operation)
 
        if operation == "read_csv":
            rel_path = step["path"]
            name = step.get("name", rel_path)
            abs_path = os.path.join(os.path.dirname(__file__), rel_path)
            print(f"Reading CSV from: {abs_path}")
            print(name)
 
            lines = sc.textFile(abs_path)
            header_line = lines.first()
            headers = header_line.split(",")
            rdd = lines.filter(lambda x: x != header_line)\
                       .map(lambda line: dict(zip(headers, line.split(","))))
            rdd_map[name] = rdd
            active_rdd = rdd
            print("Preview after read_csv:", rdd.take(5))
        
        elif operation == "read_csv_2":
 
            rel_path = step["path"]
            name = step.get("name")
            abs_path = os.path.join(os.path.dirname(__file__), rel_path)
            print(f"Reading second CSV from: {abs_path}")
            lines = sc.textFile(abs_path)
            header_line = lines.first()
            print(name)
            
 
            headers_2 = header_line.split(",")
            rdd2 = lines.filter(lambda x: x != header_line)\
                        .map(lambda line: dict(zip(headers_2, line.split(","))))
            rdd_map[name] = rdd2
            print("Preview after read_csv:", rdd2.take(5))
 
        elif operation == "join":
            left_rdd_name = step["table1"]
            right_rdd_name = step["table2"]
            join_key = step["on"]
 
            rdd1 = rdd_map.get(left_rdd_name)
            rdd2 = rdd_map.get(right_rdd_name)
            rdd1_kv = rdd1.map(lambda row: (row.get(join_key), row))
            rdd2_kv = rdd2.map(lambda row: (row.get(join_key), row))
            joined_rdd = rdd1_kv.join(rdd2_kv)
            active_rdd = joined_rdd.map(lambda pair: {**pair[1][0], **pair[1][1]})
            headers = list(set(active_rdd.first().keys()))
            print("Preview after join:", active_rdd.take(5))
 
 
 
 
        elif operation == "filter" and active_rdd:
            f = step["field"]
            op = step["operator"]
            val = step["value"]
            active_rdd = active_rdd.filter(lambda row: eval(f"row['{f}'] {op} {repr(val)}"))
            print("Preview after filter:", active_rdd.take(5))
 
        elif operation == "map" and active_rdd:
            if "rename" in step:
                old, new = step["field"], step["rename"]
                active_rdd = active_rdd.map(lambda row: {new if k == old else k: v for k, v in row.items()})
                headers = [new if h == old else h for h in headers]
            if "multiply_by" in step:
                field = step["field"]
                factor = step["multiply_by"]
                active_rdd = active_rdd.map(lambda row: {**row, field: str(float(row[field]) * float(factor))})
            if "drop" in step:
                to_drop = step["drop"]
                active_rdd = active_rdd.map(lambda row: {k: v for k, v in row.items() if k not in to_drop})
                headers = [h for h in headers if h not in to_drop]
            print("Preview after map:", active_rdd.take(5))
 
 
        elif operation == "orderBy" and active_rdd:
            keys = step["columns"]
            ascending = step.get("ascending", True)
            active_rdd = active_rdd.sortBy(lambda row: tuple(row[k] for k in keys), ascending=ascending)
            print("Preview after orderBy:", active_rdd.take(5))
 
        elif operation == "groupBy" and active_rdd:
            group_field = step["group_field"]
            agg_field = step["agg_field"]
            func = step["agg_func"]
          
 
            if func == "count":
                active_rdd = (
                    active_rdd
                    .map(lambda row: (row[group_field], 1))
                    .reduceByKey(lambda a, b: a + b)
                    .map(lambda kv: {group_field: kv[0], f"count_{agg_field}": kv[1]})
                )
            else:
                grouped = (
                    active_rdd
                    .map(lambda row: (row[group_field], float(row.get(agg_field))))
                    .groupByKey()
                    .mapValues(list)
                )
                if func == "sum":
                    active_rdd = grouped.map(lambda kv: {
                        group_field: kv[0],
                        f"sum_{agg_field}": sum(kv[1])
                    })
                elif func == "avg":
                    active_rdd = grouped.map(lambda kv: {
                        group_field: kv[0],
                        f"avg_{agg_field}": sum(kv[1]) / len(kv[1]) if kv[1] else 0
                    })
 
            headers = list(active_rdd.first().keys())
            print("Preview after groupBy:", active_rdd.take(5))
 
    return active_rdd
 
@app.route('/submit_pipeline', methods=['POST'])
def submit_pipeline():
    print(request.get_json())
    global final_output_data
    try:
        data = execute_pipeline(request.get_json()).take(100)
        if not data:
            return "<h2>No data returned</h2>"
        final_output_data = data
        return render_template_string(pd.DataFrame(data).to_html(index=False))
    except Exception as e:
        return f"<h2>Error: {e}</h2>"
 
@app.route('/table')
def table():
    if not final_output_data:
        return "<h2>No data to display</h2>"
    headers = final_output_data[0].keys()
    rows = ''.join(f"<tr>{''.join(f'<td>{row.get(h, "")}</td>' for h in headers)}</tr>" for row in final_output_data)
    html = f"""
<table border=1 style='width:90%;margin:auto;text-align:center;border-collapse:collapse'>
<tr>{''.join(f'<th>{h}</th>' for h in headers)}</tr>{rows}</table>"""
    return Response(html, mimetype='text/html')
 
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000, debug=True)