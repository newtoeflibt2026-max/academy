import io
p = "templates/mistakes.html"
s = io.open(p, encoding="utf-8").read()

# 1) inject the add-form right after the stats closing block, before {% if mistakes %}
form_html = """  <div style="background:#fff;border-radius:14px;padding:14px;margin:14px 0;box-shadow:0 2px 8px rgba(0,0,0,.06)">
    <div style="font-weight:700;margin-bottom:10px;color:#1e3a5f">➕ أضف كلمة أو خطأ لتراجعه</div>
    <input id="mw" placeholder="الكلمة أو الخطأ (مثال: accomodate)" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #cbd5e1;border-radius:8px;margin-bottom:8px;font-size:15px">
    <input id="mm" placeholder="المعنى أو الكتابة الصحيحة (مثال: accommodate / يستوعب)" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #cbd5e1;border-radius:8px;margin-bottom:8px;font-size:15px">
    <select id="mk" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #cbd5e1;border-radius:8px;margin-bottom:8px;font-size:15px">
      <option value="meaning">معنى كلمة</option>
      <option value="spelling">تصحيح إملاء (spelling)</option>
    </select>
    <button onclick="addMistake()" style="width:100%;padding:11px;background:#3b82f6;color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer">💾 احفظ في دفتري</button>
  </div>
"""
marker = "{% if mistakes %}"
if "addMistake()" in s:
    print("FORM ALREADY EXISTS")
elif marker in s:
    s = s.replace(marker, form_html + "  " + marker, 1)
    # 2) add JS function before retry function
    js_anchor = "function retry(id){"
    js_func = """function addMistake(){
  const w=document.getElementById('mw').value.trim();
  const m=document.getElementById('mm').value.trim();
  const k=document.getElementById('mk').value;
  if(!w||!m){alert('اكتب الكلمة والمعنى');return;}
  const uid=(new URLSearchParams(location.search).get('user_id')||"{{ user_id }}");
  fetch('/api/mistakes/add',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({user_id:uid,word:w,meaning:m,kind:k})})
  .then(r=>r.json()).then(res=>{if(res.success){location.reload();}else{alert('فشل الحفظ');}});
}
function retry(id){"""
    s = s.replace(js_anchor, js_func, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("FORM + JS ADDED")
else:
    print("MARKER NOT FOUND")
