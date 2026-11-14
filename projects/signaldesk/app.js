const API=window.SIGNALDESK_API||"http://127.0.0.1:8001";
let active="all";
const escapeHTML=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
async function refresh(){
  try{
    const q=document.querySelector("#search").value;
    const params=new URLSearchParams();
    if(q)params.set("q",q);
    if(active==="High")params.set("priority","High");
    if(active==="At risk")params.set("sla_state","at_risk");
    const res=await fetch(API+"/tickets?"+params);
    if(!res.ok)throw Error("Could not load tickets");
    const rows=await res.json();
    document.querySelector("#tickets").innerHTML=rows.map(t=>`
      <article class="ticket">
        <div class="ticket-id">${escapeHTML(t.id)}<span class="priority ${escapeHTML(t.priority.toLowerCase())}">${escapeHTML(t.priority.toUpperCase())}</span></div>
        <h3>${escapeHTML(t.title)}</h3><p>${escapeHTML(t.queue)} · ${escapeHTML(t.account_tier)}</p>
        <div class="ticket-foot"><span>◷ ${t.sla_state==="at_risk"?"SLA at risk":Math.max(0,Math.round(t.seconds_to_sla/60))+"m to SLA"}</span>
        <button class="assign" data-assign="${escapeHTML(t.id)}" ${t.assignee?"disabled":""}>${t.assignee?"Assigned: "+escapeHTML(t.assignee):"Assign to me"}</button></div>
        <div class="ticket-actions"><select data-status="${escapeHTML(t.id)}" aria-label="Change ticket status">
          <option value="open" ${t.status==="open"?"selected":""}>Open</option>
          <option value="in_progress" ${t.status==="in_progress"?"selected":""}>In progress</option>
          <option value="resolved" ${t.status==="resolved"?"selected":""}>Resolved</option>
        </select><button class="assign" data-events="${escapeHTML(t.id)}">History</button></div>
        <div class="ticket-history" id="history-${escapeHTML(t.id)}" hidden></div>
      </article>`).join("");
    document.querySelectorAll("[data-assign]").forEach(b=>b.addEventListener("click",()=>assign(b)));
    document.querySelectorAll("[data-status]").forEach(s=>s.addEventListener("change",()=>changeStatus(s)));
    document.querySelectorAll("[data-events]").forEach(b=>b.addEventListener("click",()=>showHistory(b.dataset.events)));
    const summary=await fetch(API+"/analytics/summary").then(r=>r.json());
    document.querySelector("#openCount").textContent=summary.open;
    document.querySelector("#riskCount").textContent=String(summary.at_risk).padStart(2,"0");
  }catch(error){console.error(error);document.querySelector("#tickets").innerHTML="<p>API unavailable. Start the SignalDesk backend and refresh.</p>";}
}
async function assign(button){
  try{const response=await fetch(API+"/tickets/"+encodeURIComponent(button.dataset.assign)+"/assign",{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({assignee:"Demo operator"})});if(!response.ok)throw Error("Assignment failed");await refresh();}
  catch(error){alert(error.message);}
}
async function changeStatus(select){
  try{const response=await fetch(API+"/tickets/"+encodeURIComponent(select.dataset.status)+"/status",{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({status:select.value})});if(!response.ok)throw Error("Status update failed");await refresh();}
  catch(error){alert(error.message);await refresh();}
}
async function showHistory(id){
  const target=document.querySelector("#history-"+CSS.escape(id));
  try{const response=await fetch(API+"/tickets/"+encodeURIComponent(id)+"/events");if(!response.ok)throw Error("History unavailable");const events=await response.json();target.innerHTML=events.map(e=>`<p><b>${escapeHTML(e.event_type)}</b> · ${escapeHTML(e.details)} <small>${escapeHTML(new Date(e.created_at).toLocaleString())}</small></p>`).join("")||"No history yet";target.hidden=!target.hidden;}
  catch(error){target.textContent=error.message;target.hidden=false;}
}
document.querySelector("#newTicketForm").addEventListener("submit",async event=>{
  event.preventDefault();const form=event.currentTarget;const data=Object.fromEntries(new FormData(form).entries());
  data.id="SD-"+crypto.randomUUID().slice(0,8).toUpperCase();data.due_at=new Date(data.due_at).toISOString();
  const message=document.querySelector("#createMessage");message.textContent="Creating…";
  try{const response=await fetch(API+"/tickets",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});const result=await response.json();if(!response.ok)throw Error(result.detail||"Could not create ticket");message.textContent="Created "+result.id;form.reset();await refresh();}
  catch(error){message.textContent=error.message;}
});
document.querySelectorAll("[data-filter]").forEach(button=>button.addEventListener("click",()=>{document.querySelector(".filters .active")?.classList.remove("active");button.classList.add("active");active=button.dataset.filter;refresh();}));
document.querySelector("#search").addEventListener("input",refresh);
refresh();
