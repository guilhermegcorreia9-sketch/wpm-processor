# -*- coding: utf-8 -*-
# Created by Miguel Alexandre da Cunha
import sys
import os
import json
import traceback

def main():
    if len(sys.argv) != 4:
        print("ERROR: uso: subprocess_runner.py <mode> <params_json_path> <result_json_path>", flush=True)
        sys.exit(2)

    mode, params_path, result_path = sys.argv[1], sys.argv[2], sys.argv[3]

    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)

    from core.pipeline import run_pipeline, search_available_scenes, PipelineError, PipelineCancelled

    with open(params_path, "r", encoding="utf-8") as f:
        params = json.load(f)

    def log(*args):
        print("LOG: " + " ".join(str(a) for a in args), flush=True)

    def should_cancel():
        return False

    result = {"ok": False, "outputs": [], "results": [], "error": None}
    try:
        if mode == "process":
            outputs = run_pipeline(params, log=log, should_cancel=should_cancel)
            result["ok"] = True
            result["outputs"] = outputs
        elif mode == "search":
            results = search_available_scenes(params, log=log)
            result["ok"] = True
            result["results"] = results
        else:
            raise ValueError("Modo desconhecido: {}".format(mode))
    except (PipelineError, PipelineCancelled) as exc:
        result["error"] = str(exc)
    except Exception as exc:
        result["error"] = "Erro inesperado: {}\n\n{}".format(exc, traceback.format_exc())

    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f)

    sys.exit(0 if result["ok"] else 1)

if __name__ == "__main__":
    main()
