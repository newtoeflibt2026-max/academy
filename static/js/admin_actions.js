(function(){"use strict";var A="/api/admin";
function T(m,t){t=t||"info";var b=t==="success"?"#10b981":t==="error"?"#ef4444":t==="warning"?"#f59e0b":"#3b82f6";
var d=document.createElement("div");d.textContent=m;
Object.assign(d.style,{position:"fixed",bottom:"24px",right:"24px",backgroundColor:b,color:"#fff",padding:"12px 24px",borderRadius:"8px",zIndex:"9999",fontFamily:"Tahoma,sans-serif",fontSize:"14px",boxShadow:"0 4px 12px rgba(0,0,0,0.25)"});
document.body.appendChild(d);setTimeout(function(){d.style.opacity="0";setTimeout(function(){d.remove()},300)},3000)}
async function F(u,o){try{var r=await fetch(u,o);var d=await r.json();return d}catch(e){T("Network error: "+e.message,"error");return{success:false,error:e.message}}}
function S(i,v){var e=document.getElementById(i);if(e)e.textContent=v!==undefined?v:"0"}
function E(s){return s?String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"):""}
async function LS(){var r=await F(A+"/stats");if(!r.success)return;var d=r.data;S("stat-total-students",d.total_students);S("stat-active-students",d.active_students);S("stat-pending-payments",d.pending_payments)}
async function LST(){var tb=document.getElementById("students-table-body");if(!tb)return;
var r=await F(A+"/students");if(!r.success){tb.innerHTML='<tr><td colspan="6" style="color:red;">Failed</td></tr>';return}
var ss=r.data||[];if(!ss.length){tb.innerHTML='<tr><td colspan="6">No students</td></tr>';return}
tb.innerHTML=ss.map(function(s){var a=s.is_active?"Active":"Inactive";
return '<tr><td>'+E(s.id)+'</td><td>'+E(s.name||"N/A")+'</td><td>'+E(s.path||"N/A")+'</td><td>'+E(s.placement_band||"N/A")+'</td><td>'+a+'</td><td>'
+'<button class="tg-btn" data-sid="'+s.id+'">Toggle</button> '
+'<button class="ex-btn" data-sid="'+s.id+'" data-name="'+E(s.name||"")+'">Extend</button></td></tr>'}).join("");
tb.querySelectorAll(".tg-btn").forEach(function(b){b.onclick=function(){TG(parseInt(this.dataset.sid))}});
tb.querySelectorAll(".ex-btn").forEach(function(b){b.onclick=function(){EX(parseInt(this.dataset.sid),this.dataset.name)}})}
async function TG(sid){var r=await F(A+"/student/toggle_active/"+sid,{method:"POST"});
if(r.success){T(r.message||"Updated","success");LST();LS()}else{T(r.error||"Failed","error")}}
async function EX(sid,name){var d=prompt("Days to extend for "+(name||"student "+sid)+":","30");if(d===null)return;
var dn=parseInt(d);if(isNaN(dn)||dn<=0){T("Invalid number","warning");return}
var r=await F(A+"/student/extend_subscription",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({student_id:sid,days:dn})});
if(r.success){T(r.message||"Extended","success");LST();LS()}else{T(r.error||"Failed","error")}}
async function LPP(){var c=document.getElementById("pending-payments-container");if(!c)return;
var r=await F(A+"/payments/pending");if(!r.success){c.innerHTML='<p style="color:red;">Failed</p>';return}
var ps=r.data||[];if(!ps.length){c.innerHTML='<p>No pending payments</p>';return}
c.innerHTML=ps.map(function(p){return '<div class="pcard"><span><strong>'+E(p.student_name||"?")+'</strong> '+E(p.plan)+' '+E(p.amount)+' JOD</span><div><button class="app-btn" data-pid="'+p.id+'">Approve</button> <button class="rej-btn" data-pid="'+p.id+'">Reject</button></div></div>'}).join("");
c.querySelectorAll(".app-btn").forEach(function(b){b.onclick=function(){AP(parseInt(this.dataset.pid))}});
c.querySelectorAll(".rej-btn").forEach(function(b){b.onclick=function(){RP(parseInt(this.dataset.pid))}})}
async function AP(pid){var r=await F(A+"/payment/approve/"+pid,{method:"POST"});
if(r.success){T(r.message||"Approved","success");LPP();LS()}else{T(r.error||"Failed","error")}}
async function RP(pid){var r=await F(A+"/payment/reject/"+pid,{method:"POST"});
if(r.success){T(r.message||"Rejected","success");LPP();LS()}else{T(r.error||"Failed","error")}}
function init(){
LS();setInterval(LS,60000);
var rf=document.getElementById("btn-refresh-stats");if(rf)rf.onclick=LS;
var ls=document.getElementById("btn-load-students");if(ls)ls.onclick=LST;
var lp=document.getElementById("btn-load-payments");if(lp)lp.onclick=LPP;
var cards={stat_total:"students",stat_active:"students",stat_pending:"payments"};
Object.keys(cards).forEach(function(k){var ids=["stat-total-students","stat-active-students","stat-pending-payments"];
ids.forEach(function(id){var e=document.getElementById(id);if(e&&e.parentElement){e.parentElement.style.cursor="pointer";
e.parentElement.onclick=function(){if(id.includes("payment"))LPP();else LST()}}})})}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init()})();
