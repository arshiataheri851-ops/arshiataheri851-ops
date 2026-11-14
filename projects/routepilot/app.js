const API=window.ROUTEPILOT_API||"http://127.0.0.1:8000";
const filter=document.querySelector("#statusFilter");
const escapeHTML=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
async function loadDeliveries(){
  try{
    const status=filter.value==="all"?"":filter.value.toLowerCase().replace(" ","_");
    const res=await fetch(API+"/deliveries"+(status?"?status="+encodeURIComponent(status):""));
    if(!res.ok)throw Error("Could not load deliveries");
    const rows=await res.json();
    document.querySelector("#jobs").innerHTML=rows.map(d=>{
      const label={in_transit:"In transit",delivered:"Delivered",attention:"Attention",scheduled:"Scheduled",cancelled:"Cancelled"}[d.status]||d.status;
      const cls=d.status==="delivered"?"green":d.status==="attention"?"amber":"blue";
      return `<tr><td>${escapeHTML(d.id)}</td><td>${escapeHTML(d.recipient)}</td><td>${escapeHTML(d.route_id)}</td><td>${escapeHTML(d.eta||"—")}</td><td><span class="tag ${cls}">${label}</span></td><td>${d.proof_count?"Recorded":"Pending"}</td><td><button class="proof-action" data-proof="${escapeHTML(d.id)}" ${d.proof_count?"disabled":""}>${d.proof_count?"Proof saved":"Record proof"}</button></td></tr>`;
    }).join("");
    document.querySelectorAll("[data-proof]").forEach(button=>button.addEventListener("click",()=>recordProof(button)));
  }catch(error){console.error(error);document.querySelector("#jobs").innerHTML="<tr><td colspan='7'>API unavailable. Start the RoutePilot backend and refresh.</td></tr>";}
}
async function recordProof(button){
  const recipient_name=prompt("Name of the person receiving the delivery:");
  if(!recipient_name)return;
  const note=prompt("Delivery note (optional):")||"";
  try{const response=await fetch(API+"/deliveries/"+encodeURIComponent(button.dataset.proof)+"/proof",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({recipient_name,method:"manual",note})});const data=await response.json();if(!response.ok)throw Error(data.detail||"Could not save proof");await loadDeliveries();}
  catch(error){alert(error.message);}
}
filter.addEventListener("change",loadDeliveries);
document.querySelector("#newDeliveryForm").addEventListener("submit",async event=>{
  event.preventDefault();const form=event.currentTarget;const data=Object.fromEntries(new FormData(form).entries());
  if(!data.vehicle_id)delete data.vehicle_id;
  if(data.eta)data.eta=new Date(data.eta).toISOString();else delete data.eta;
  const message=document.querySelector("#deliveryMessage");message.textContent="Creating…";
  try{const response=await fetch(API+"/deliveries",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});const result=await response.json();if(!response.ok)throw Error(result.detail||"Could not create delivery");message.textContent="Created "+result.id;form.reset();await loadDeliveries();}
  catch(error){message.textContent=error.message;}
});
document.querySelector("#generate").addEventListener("click",async()=>{
  const button=document.querySelector("#generate");
  try{const res=await fetch(API+"/deliveries/DL-2083/note");if(!res.ok)throw Error("API unavailable");const data=await res.json();button.textContent="Delivery note preview loaded";const paper=document.querySelector("#paper");paper.dataset.document=JSON.stringify(data);paper.querySelector(".paper-head span").textContent="API PREVIEW · NOT LEGAL";
  }catch(error){button.textContent="Start API to generate note";}
});
loadDeliveries();
