# Node-RED Spark Pipeline Builder

This project is a **drag-and-drop workflow builder** for Spark RDD pipelines, powered by a **Node-RED frontend**, a **Flask backend**, and **Apache Spark** running locally. It allows users to visually construct data processing flows and execute them seamlessly.

## Getting Started

### 1. Run the Flask + Spark Backend

Make sure you have all dependencies installed, then start the backend with:

```bash
python app.py
```

This will start the Flask server at `http://localhost:5000`.

### 2. Set Up Node-RED

- Open [Node-RED](http://localhost:1880) in your browser.
- Import the pre-built flow:

  1. Open the menu (top right) → *Import*.
  2. Paste the contents of `nodered-flow.json`.
  3. Click *Import* to load the drag-and-drop blocks and example flows.

### 3. Run a Workflow

- Click the **inject** button on the 'Read CSV' to trigger the pipeline.
- A request will be sent to the Flask backend.
- After processing, the results will be available at:

```
http://localhost:5000/table
```

This page displays the output of your Spark pipeline in an HTML table.

## Dependencies

Make sure the following are installed:

- Python 3.x
- Flask
- PySpark
- Node-RED
