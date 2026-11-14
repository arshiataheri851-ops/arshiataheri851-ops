export default {
 async fetch(request, env) {
  const allowed = (env.ALLOWED_ORIGINS || "").split(",").map(v => v.trim()).filter(Boolean);
  const origin = request.headers.get("Origin") || "";
  const cors = allowed.includes(origin) ? {
   "Access-Control-Allow-Origin": origin,
   "Access-Control-Allow-Methods": "POST, OPTIONS",
   "Access-Control-Allow-Headers": "Content-Type",
   "Vary": "Origin"
  } : {};
  const respond = (body, status=200) => new Response(JSON.stringify(body), {
   status, headers: { "Content-Type":"application/json; charset=utf-8", "Cache-Control":"no-store", "X-Content-Type-Options":"nosniff", ...cors }
  });
  if (request.method === "OPTIONS") return new Response(null, {status:204,headers:cors});
  if (request.method !== "POST") return respond({error:"Method not allowed"},405);
  if (!allowed.includes(origin)) return respond({error:"Origin not allowed"},403);
  if (!(request.headers.get("Content-Type") || "").toLowerCase().includes("application/json")) return respond({error:"JSON required"},415);
  const length = Number(request.headers.get("Content-Length") || "0");
  if (length > 9000) return respond({error:"Request too large"},413);
  let data;
  try { data = await request.json(); } catch { return respond({error:"Invalid JSON"},400); }
  const str = (v,max) => typeof v === "string" && v.trim().length <= max ? v.trim() : null;
  const name = str(data.name,80), email = str(data.email,254), company = str(data.company || "",100);
  const service = str(data.service,100), message = str(data.message,3000), honeypot = str(data.website || "",200);
  if (honeypot) return respond({ok:true});
  if (data.consent !== "true" || !name || name.length < 2 || !email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || !service || !message || message.length < 20) return respond({error:"Please check the submitted fields"},400);
  if (!env.RESEND_API_KEY || !env.CONTACT_TO || !env.CONTACT_FROM) return respond({error:"Service is not configured"},503);
  const textBody = [
   "New ERYNDEX project inquiry","",
   "Name: " + name,"Email: " + email,"Company: " + company,
   "Service: " + service,"","Project brief:",message
  ].join("\n");
  const sent = await fetch("https://api.resend.com/emails", {
   method:"POST",
   headers:{ "Authorization":"Bearer " + env.RESEND_API_KEY, "Content-Type":"application/json" },
   body:JSON.stringify({from:env.CONTACT_FROM,to:[env.CONTACT_TO],reply_to:email,subject:"New ERYNDEX project inquiry",text:textBody})
  });
  if (!sent.ok) return respond({error:"Unable to deliver inquiry"},502);
  return respond({ok:true},200);
 }
};
