const toggle=document.getElementById('menuToggle');const nav=document.getElementById('nav');toggle?.addEventListener('click',()=>{const open=nav.classList.toggle('open');toggle.setAttribute('aria-expanded',String(open));});nav?.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{nav.classList.remove('open');toggle?.setAttribute('aria-expanded','false');}));const progress=document.getElementById('progress');window.addEventListener('scroll',()=>{const max=document.documentElement.scrollHeight-window.innerHeight;progress.style.width=(max>0?window.scrollY/max*100:0)+'%';},{passive:true});const year=document.getElementById('year');if(year) year.textContent=new Date().getFullYear();
const contactForm=document.getElementById('contactForm');
contactForm?.addEventListener('submit',async event=>{
 event.preventDefault();
 const status=document.getElementById('formStatus');
 if(!contactForm.reportValidity()) return;
 if(document.getElementById('website')?.value) return;
 const data=Object.fromEntries(new FormData(contactForm).entries());
 if(data.name.trim().length<2||data.message.trim().length<20||data.message.length>3000){status.textContent='Please check the name and project brief.';return;}
 const endpoint=window.ERYNDEX_CONTACT_ENDPOINT||'';
 if(!endpoint){
  const subject=encodeURIComponent('Project inquiry — ERYNDEX');
  const body=encodeURIComponent('Name: '+data.name+'\nEmail: '+data.email+'\nCompany: '+data.company+'\nService: '+data.service+'\n\nBrief:\n'+data.message);
  window.location.href='mailto:eryndexco@gmail.com?subject='+subject+'&body='+body;
  status.textContent='Your email app should open with the inquiry details. Online form delivery will be enabled after the secure backend is deployed.';
  return;
 }
 const button=contactForm.querySelector('button[type="submit"]');button.disabled=true;status.textContent='Sending…';
 try{
  const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const result=await response.json();
  if(!response.ok) throw new Error(result.error||'Submission failed');
  contactForm.reset();status.textContent='Thank you. Your inquiry has been received.';
 }catch(error){status.textContent='We could not send the inquiry. Please email eryndexco@gmail.com.';}
 finally{button.disabled=false;}
});
