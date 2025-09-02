@@ .. @@
 
 logger = logging.getLogger(__name__)
 
+# Проверяем наличие API ключа
+GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
+if not GEMINI_API_KEY:
+    logger.error("❌ GEMINI_API_KEY not found in environment variables")
+    raise ValueError("GEMINI_API_KEY is required")
+
+# Настраиваем Gemini
+genai.configure(api_key=GEMINI_API_KEY)
+model = genai.GenerativeModel('gemini-2.0-flash-exp')
+
 async def extract_drugs_from_text(text: str) -> List[Dict]:
     """
     Извлекает информацию о препаратах из текста, используя точно такой же промпт как в демо версии
@@ .. @@
     
     try:
         logger.info("🤖 Calling Gemini API for drug extraction...")
-        
-        # Настраиваем Gemini
-        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
-        if not GEMINI_API_KEY:
-            raise ValueError("GEMINI_API_KEY not found in environment variables")
-        
-        genai.configure(api_key=GEMINI_API_KEY)
-        model = genai.GenerativeModel('gemini-2.0-flash-exp')
-        
         response = model.generate_content(prompt)
         
         if not response or not response.text:
@@ .. @@
     
     try:
         logger.info("📝 Generating document summary with Gemini...")
-        
-        # Настраиваем Gemini
-        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
-        if not GEMINI_API_KEY:
-            raise ValueError("GEMINI_API_KEY not found in environment variables")
-        
-        genai.configure(api_key=GEMINI_API_KEY)
-        model = genai.GenerativeModel('gemini-2.0-flash-exp')
-        
         response = model.generate_content(summary_prompt)
         
         if response and response.text: