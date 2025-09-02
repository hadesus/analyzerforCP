@@ .. @@
 @app.get("/")
 def read_root():
     logger.info("Health check endpoint called")
+    
+    # Проверяем статус BNF файлов
+    try:
+        from services.bnf_analyzer import bnf_analyzer
+        bnf_stats = bnf_analyzer.get_bnf_stats()
+    except Exception as e:
+        logger.error(f"Error getting BNF stats: {e}")
+        bnf_stats = {"error": str(e)}
+    
     return {
         "message": "Clinical Protocol Analysis API is running.",
         "timestamp": datetime.datetime.now().isoformat(),
         "status": "healthy",
         "imports_status": {
             "pipeline": run_analysis_pipeline is not None,
             "exporter": create_docx_export is not None
-        }
+        },
+        "bnf_status": bnf_stats
     }