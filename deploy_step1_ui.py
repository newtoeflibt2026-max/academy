import os

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "admin_dashboard.html")

html = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Yamen Academy Admin</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',Tahoma,sans-serif;background:#f0f2f5;color:#333}
.header{background:linear-gradient(135deg,#1a237e,#283593);color:white;padding:1.5rem 2rem}
.header h1{font-size:1.8rem}
.header p{opacity:0.8;margin-top:0.3rem}
.nav{background:white;padding:0.8rem 2rem;display:flex;gap:1rem;border-bottom:1px solid #e0e0e0}
.nav a{text-decoration:none;color:#1a237e;font-weight:bold;padding:0.4rem 1rem;border-radius:6px}
.nav a:hover{background:#1a237e;color:white}
.container{max-width:1200px;margin:2rem auto;padding:0 1rem}
.panel{background:white;border-radius:16px;padding:2rem;margin-bottom:2rem;box-shadow:0 4px 16px rgba(0,0,0,0.06)}
.panel h2{color:#1a237e;margin-bottom:1.5rem;border-bottom:2px solid #e0e0e0;padding-bottom:0.5rem}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin-bottom:2rem}
.stat-card{background:#e8eaf6;padding:1.5rem;border-radius:12px;text-align:center}
.stat-card .value{font-size:2rem;font-weight:bold;color:#1a237e}
.stat-card .label{font-size:0.9rem;color:#666}
.form-group{margin-bottom:1rem}
.form-group label{display:block;font-weight:bold;margin-bottom:0.3rem}
.form-group input,.form-group textarea,.form-group select{width:100%;padding:0.6rem;border:1px solid #ddd;border-radius:8px;font-size:0.95rem}
.form-group textarea{min-height:80px;resize:vertical}
.form-row{display:flex;gap:1rem}
.form-row .form-group{flex:1}
button{background:#1a237e;color:white;border:none;padding:0.7rem 2rem;border-radius:8px;font-size:1rem;cursor:pointer;font-weight:bold}
button:hover{background:#283593}
button.danger{background:#c62828}
button.danger:hover{background:#b71c1c}
.question-item{background:#f5f5f5;padding:1rem;border-radius:8px;margin-bottom:0.8rem;display:flex;justify-content:space-between;align-items:center}
.question-item .q-text{flex:1}
.question-item .actions{display:flex;gap:0.5rem}
.badge{padding:0.2rem 0.7rem;border-radius:20px;font-size:0.75rem;font-weight:bold}
.badge-reading{background:#ffcdd2;color:#c62828}
.badge-listening{background:#bbdefb;color:#1565c0}
.badge-writing{background:#c8e6c9;color:#2e7d32}
.badge-speaking{background:#ffe0b2;color:#e65100}
.badge-grammar{background:#e1bee7;color:#6a1b9a}
.badge-vocabulary{background:#b2ebf2;color:#00838f}
.hidden{display:none}
#result{margin-top:1rem;padding:1rem;border-radius:8px}
.success-msg{background:#c8e6c9;color:#2e7d32}
.error-msg{background:#ffcdd2;color:#c62828}
</style>
</head>
<body>
<div class="header">
<h1>Yamen Academy Admin</h1>
<p>Manage lessons, questions, and placement tests</p>
</div>
<div class="nav">
<a href="/dashboard">Dashboard</a>
<a href="/lessons">Lessons</a>
<a href="#" onclick="loadQuestions();return false">Questions</a>
<a href="#" onclick="showAddQuestion();return false">+ Add Question</a>
</div>
<div class="container">
<div class="stats" id="stats">
<div class="stat-card"><div class="value" id="stat-questions">-</div><div class="label">Questions</div></div>
<div class="stat-card"><div class="value" id="stat-lessons">-</div><div class="label">Lessons</div></div>
<div class="stat-card"><div class="value" id="stat-students">-</div><div class="label">Students</div></div>
</div>
<div class="panel hidden" id="question-form-panel">
<h2 id="form-title">Add Question</h2>
<input type="hidden" id="edit-id" value="">
<div class="form-group"><label>Skill</label><select id="q-skill"><option>reading</option><option>listening</option><option>writing</option><option>speaking</option><option>grammar</option><option>vocabulary</option></select></div>
<div class="form-group"><label>Question</label><textarea id="q-text" placeholder="Enter question text..."></textarea></div>
<div class="form-row">
<div class="form-group"><label>Option A</label><input id="q-a" placeholder="Option A"></div>
<div class="form-group"><label>Option B</label><input id="q-b" placeholder="Option B"></div>
</div>
<div class="form-row">
<div class="form-group"><label>Option C</label><input id="q-c" placeholder="Option C"></div>
<div class="form-group"><label>Option D</label><input id="q-d" placeholder="Option D"></div>
</div>
<div class="form-row">
<div class="form-group"><label>Correct Answer</label><select id="q-answer"><option>A</option><option>B</option><option>C</option><option>D</option></select></div>
<div class="form-group"><label>Difficulty</label><select id="q-diff"><option>beginner</option><option>intermediate</option><option>advanced</option></select></div>
</div>
<div style="margin-top:1rem;display:flex;gap:1rem">
<button onclick="saveQuestion()">Save</button>
<button class="danger" onclick="hideForm()">Cancel</button>
</div>
<div id="result"></div>
</div>
<div class="panel" id="questions-panel">
<h2>All Questions <span style="font-size:0.9rem;color:#888" id="q-count"></span></h2>
<div id="questions-list">Loading...</div>
</div>
</div>
<script>
const API=(url,method='GET',body=null)=>fetch(url,{method,headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):null}).then(r=>r.json());
async function loadStats(){try{const qs=await API('/api/admin/questions');document.getElementById('stat-questions').textContent=qs.length;const idx=await API('/api/index');document.getElementById('stat-lessons').textContent=idx.total_lessons||'-'}catch(e){console.error(e)}}
async function loadQuestions(){document.getElementById('question-form-panel').classList.add('hidden');const c=document.getElementById('questions-list');const ce=document.getElementById('q-count');try{const qs=await API('/api/admin/questions');ce.textContent='('+qs.length+' questions)';if(!qs.length){c.innerHTML='<p style="color:#999">No questions yet</p>';return}c.innerHTML=qs.map(q=>{const bc='badge-'+q.skill;return'<div class="question-item"><div class="q-text"><span class="badge '+bc+'">'+q.skill+'</span> <strong>'+q.question.substring(0,80)+(q.question.length>80?'...':'')+'</strong><br><small style="color:#888">Answer: '+q.correct_answer+' | Level: '+q.difficulty+'</small></div><div class="actions"><button onclick="editQuestion('+q.id+')" style="padding:0.3rem 0.8rem;font-size:0.85rem">Edit</button><button onclick="deleteQuestion('+q.id+')" class="danger" style="padding:0.3rem 0.8rem;font-size:0.85rem">Delete</button></div></div>'});loadStats()}catch(e){c.innerHTML='<p style="color:#c62828">Error: '+e.message+'</p>'}}
function showAddQuestion(){document.getElementById('edit-id').value='';document.getElementById('form-title').textContent='Add Question';['q-text','q-a','q-b','q-c','q-d'].forEach(id=>document.getElementById(id).value='');document.getElementById('q-skill').value='reading';document.getElementById('q-answer').value='A';document.getElementById('q-diff').value='beginner';document.getElementById('result').innerHTML='';document.getElementById('question-form-panel').classList.remove('hidden');window.scrollTo(0,0)}
function hideForm(){document.getElementById('question-form-panel').classList.add('hidden')}
async function editQuestion(id){const qs=await API('/api/admin/questions');const q=qs.find(x=>x.id===id);if(!q)return;document.getElementById('edit-id').value=q.id;document.getElementById('form-title').textContent='Edit Question #'+q.id;document.getElementById('q-skill').value=q.skill;document.getElementById('q-text').value=q.question;document.getElementById('q-a').value=q.option_a;document.getElementById('q-b').value=q.option_b;document.getElementById('q-c').value=q.option_c;document.getElementById('q-d').value=q.option_d;document.getElementById('q-answer').value=q.correct_answer;document.getElementById('q-diff').value=q.difficulty||'beginner';document.getElementById('result').innerHTML='';document.getElementById('question-form-panel').classList.remove('hidden');window.scrollTo(0,0)}
async function saveQuestion(){const editId=document.getElementById('edit-id').value;const data={skill:document.getElementById('q-skill').value,question:document.getElementById('q-text').value,option_a:document.getElementById('q-a').value,option_b:document.getElementById('q-b').value,option_c:document.getElementById('q-c').value,option_d:document.getElementById('q-d').value,correct_answer:document.getElementById('q-answer').value,difficulty:document.getElementById('q-diff').value};const rd=document.getElementById('result');try{let res;if(editId){res=await API('/api/admin/questions/edit/'+editId,'POST',data)}else{res=await API('/api/admin/questions/add','POST',data)}if(res.status==='ok'){rd.innerHTML='<div class="success-msg">Saved!</div>';setTimeout(()=>{hideForm();loadQuestions()},1000)}else{rd.innerHTML='<div class="error-msg">Error: '+(res.error||res.message||'Unknown')+'</div>'}}catch(e){rd.innerHTML='<div class="error-msg">Error: '+e.message+'</div>'}}
async function deleteQuestion(id){if(!confirm('Delete question #'+id+'?'))return;try{const res=await API('/api/admin/questions/delete/'+id,'POST');alert(res.message);loadQuestions()}catch(e){alert('Error: '+e.message)}}
loadQuestions();
</script>
</body>
</html>"""

with open(TEMPLATE, "w", encoding="utf-8") as f:
    f.write(html)
print("admin_dashboard.html generated!")
