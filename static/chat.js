(function(){
  var input=document.getElementById('goal-input');
  var run=document.getElementById('run-goal');
  var conversation=document.getElementById('conversation');
  var samples=document.querySelectorAll('.sample-request');
  var sessionId='session_'+Math.random().toString(36).slice(2)+'_'+Date.now();

  function escapeHtml(value){
    return String(value).replace(/[&<>'"]/g,function(ch){return {'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch];});
  }

  function addBubble(text, cls, speaker){
    var s=document.createElement('div');
    s.className='speaker';
    s.textContent=speaker;
    var b=document.createElement('div');
    b.className='bubble '+cls;
    b.innerHTML=escapeHtml(text).replace(/\n/g,'<br>');
    conversation.appendChild(s);
    conversation.appendChild(b);
    conversation.scrollTop=conversation.scrollHeight;
  }

  function setRunning(isRunning){
    run.disabled=isRunning;
    run.textContent=isRunning?'Running':'Run';
  }

  function delay(ms){
    return new Promise(function(resolve){window.setTimeout(resolve,ms);});
  }

  function waitForFrameLoad(frame){
    return new Promise(function(resolve){
      var done=false;
      function finish(){if(!done){done=true;resolve();}}
      frame.addEventListener('load',finish,{once:true});
      window.setTimeout(finish,2500);
    });
  }

  function getFrames(){
    var outer=document.querySelector('.legacy-outer-frame');
    if(!outer || !outer.contentWindow){return null;}
    var workspace=outer.contentWindow.document.querySelector('iframe[name="workspace"]');
    if(!workspace || !workspace.contentWindow){return null;}
    return {outer:outer,workspace:workspace,doc:workspace.contentWindow.document};
  }

  function markLiveStep(text){
    var status=document.getElementById('live-status');
    if(status){status.textContent=text;}
  }

  async function resetWorkspace(){
    var frames=getFrames();
    if(!frames){return null;}
    frames.workspace.src='/legacy/member-inquiry';
    await waitForFrameLoad(frames.workspace);
    await delay(250);
    return getFrames();
  }

  async function runLiveWorkflow(capability,args){
    if(capability!=='lookup_balance' || !args){return;}
    var frames=await resetWorkspace();
    if(!frames){return;}

    markLiveStep('Entering member '+args.member_id);
    var doc=frames.doc;
    var inputEl=doc.querySelector('input[name="member_number"]');
    if(inputEl){
      inputEl.focus();
      inputEl.value='';
      await delay(250);
      var chars=String(args.member_id||'').split('');
      for(var i=0;i<chars.length;i++){
        inputEl.value+=chars[i];
        inputEl.dispatchEvent(new Event('input',{bubbles:true}));
        await delay(80);
      }
    }

    markLiveStep('Finding member');
    await delay(350);
    var form=doc.querySelector('form');
    if(form){form.submit();}
    await waitForFrameLoad(frames.workspace);
    await delay(500);

    frames=getFrames();
    if(!frames){return;}
    doc=frames.doc;
    markLiveStep('Opening '+args.account_type+' account');
    var desired=args.account_type==='checking'?'DDA':'SAV';
    var rows=Array.prototype.slice.call(doc.querySelectorAll('.accounts-table tr'));
    for(var r=0;r<rows.length;r++){
      if(rows[r].textContent.indexOf(desired)!==-1){
        var link=rows[r].querySelector('a.view-link');
        if(link){
          link.click();
          await waitForFrameLoad(frames.workspace);
          await delay(500);
          markLiveStep('Reading current balance');
          return;
        }
      }
    }
  }

  async function runGoal(){
    var goal=input.value.trim();
    if(!goal){return;}
    addBubble(goal,'user-bubble','YOU');
    input.value='';
    setRunning(true);
    try{
      var response=await fetch('/api/chat/prepare',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({session_id:sessionId,message:goal})
      });
      var result=await response.json();
      if(result.status==='ready'){
        addBubble('Running the approved lookup now. Watch the legacy app on the left.','assistant-bubble','ASSISTANT');
        var livePromise=runLiveWorkflow(result.capability,result.data);
        var replayResponse=await fetch('/api/chat/replay',{
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({session_id:sessionId,capability:result.capability,arguments:result.data||{}})
        });
        var replayResult=await replayResponse.json();
        await livePromise;
        addBubble(replayResult.message || 'No response returned.','assistant-bubble','ASSISTANT');
      }else{
        addBubble(result.message || 'No response returned.','assistant-bubble','ASSISTANT');
      }
    }catch(err){
      addBubble('The request could not be completed right now.','assistant-bubble','ASSISTANT');
    }finally{
      setRunning(false);
      markLiveStep('Ready');
      input.focus();
    }
  }

  for(var i=0;i<samples.length;i++){
    samples[i].addEventListener('click',function(){input.value=this.textContent;input.focus();});
  }
  run.addEventListener('click',function(){runGoal();});
  input.addEventListener('keydown',function(e){if(e.key==='Enter' && !e.shiftKey){e.preventDefault();runGoal();}});
})();
