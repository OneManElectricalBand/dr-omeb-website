import test from 'node:test';
import assert from 'node:assert/strict';
import {createHandler} from '../src/index.mjs';
const origin = 'https://dr-omeb-website.pages.dev';
const good = {name:'Test Visitor',email:'visitor@example.com',reason:'General',message:'Contact delivery test',token:'valid',consent:true};
function env() { return {TURNSTILE_SITE_KEY:'public',TURNSTILE_SECRET_KEY:'secret',MAILERLITE_API_TOKEN:'private',MAILERLITE_GROUP_ID:'group',MAILERLITE_DOUBLE_OPT_IN_READY:'true',CONTACT_TO:'owner@example.com',CONTACT_FROM:'hello@example.com',FORM_LIMITER:{limit:async()=>({success:true})},EMAIL:{send:async()=>{}}}; }
function req(path='/contact',body=good,extra={}) { return new Request(`https://forms.example${path}`,{method:'POST',headers:{Origin:origin,'Content-Type':'application/json','CF-Connecting-IP':'192.0.2.1',...extra},body:JSON.stringify(body)}); }
const verified = action => Response.json({success:true,hostname:'dr-omeb-website.pages.dev',action});
test('missing or incorrect Turnstile verification never delivers', async()=>{
  for(const result of [{success:false},{success:true,hostname:'evil.example',action:'contact'},{success:true,hostname:'dr-omeb-website.pages.dev',action:'signup'}]) {
    let sent=0; const bindings=env(); bindings.EMAIL.send=async()=>sent++;
    const response=await createHandler(async()=>Response.json(result))(req(),bindings);
    assert.equal(response.status,400); assert.equal(sent,0);
  }
});
test('contact sends only to fixed owner with visitor reply-to',async()=>{
  let mail; const bindings=env(); bindings.EMAIL.send=async value=>{mail=value;};
  const response=await createHandler(async()=>verified('contact'))(req('/contact',{...good,to:'attacker@example.com'}),bindings);
  assert.equal(response.status,200); assert.equal(mail.to,'owner@example.com'); assert.equal(mail.from,'hello@example.com'); assert.equal(mail.replyTo,good.email); assert.match(mail.text,/Contact delivery test/);
});
test('rejects malformed, oversize, honeypot, missing consent and untrusted origin before verification',async()=>{
  let calls=0;const handler=createHandler(async()=>{calls++;throw Error();});
  for(const request of [req('/contact',{...good,email:'bad\r\nBcc: attacker@example.com'}),req('/contact',{...good,website:'bot'}),req('/contact',{...good,message:'x'.repeat(17000)}),req('/signup',{...good,consent:false}),req('/contact',good,{Origin:'https://evil.example'}),req('/contact',{...good,token:''})]) assert.ok((await handler(request,env())).status>=400);
  assert.equal(calls,0);
});
test('rate limited request never invokes providers',async()=>{
 const bindings=env();bindings.FORM_LIMITER.limit=async()=>({success:false});
 assert.equal((await createHandler(async()=>{throw Error('must not call');})(req(),bindings)).status,429);
});
test('signup requires verified API double opt-in configuration',async()=>{
 const bindings=env();bindings.MAILERLITE_DOUBLE_OPT_IN_READY='false';
 assert.equal((await createHandler(async()=>{throw Error('must not call');})(req('/signup'),bindings)).status,503);
});
test('signup preserves existing opt-outs and profile data',async()=>{
 for(const status of ['unsubscribed','bounced','junk','active']) {
  let write;const handler=createHandler(async(url,options)=>{
   if(url.includes('siteverify'))return verified('signup');
   if(!options.method)return Response.json({data:{status,fields:{name:'Original'}}});
   write=JSON.parse(options.body);return Response.json({data:{status}});
  });
  assert.equal((await handler(req('/signup'),env())).status,200);
  if(status==='active')assert.deepEqual(write,{email:good.email,groups:['group']});else assert.equal(write,undefined);
 }
});
test('new signup adds only intended group without forcing confirmed status',async()=>{
 let write;const handler=createHandler(async(url,options)=>{
  if(url.includes('siteverify'))return verified('signup');
  if(!options.method)return new Response(null,{status:404});
  write=JSON.parse(options.body);return Response.json({data:{status:'unconfirmed'}},{status:201});
 });
 assert.equal((await handler(req('/signup'),env())).status,200);
 assert.deepEqual(write,{email:good.email,groups:['group'],fields:{name:good.name}});
});
test('provider delivery failure cannot report success or expose secrets',async()=>{
 const bindings=env();bindings.EMAIL.send=async()=>{throw Error('private provider details');};
 const response=await createHandler(async()=>verified('contact'))(req(),bindings);
 assert.equal(response.status,502);assert.doesNotMatch(await response.text(),/private provider/);
});
