# -*- coding: utf-8 -*-
"""给页面注入「本地存储 ⇄ 容器 /api/state」同步脚本（幂等）。

用法：python inject_sync.py <file1> [file2 ...]
没有 API（file:// 打开、资料库内嵌、纯 nginx 托管）时静默降级为纯本地存储。
"""
import io
import sys

SHIM = """<script>
/* ===== 数据同步：localStorage ⇄ 容器内 /api/state（SQLite） ===== */
(function(){
  var API="/api/state", TS="__cp_ts";
  function syncKey(k){
    return !!k && (k.indexOf("check_")===0 || k==="cnma_wrongbook_v1" ||
                   k==="raz_aa_count" || k==="weekdone" || k==="movies");
  }
  function snap(){
    var o={};
    for(var i=0;i<localStorage.length;i++){
      var k=localStorage.key(i);
      if(syncKey(k)) o[k]=localStorage.getItem(k);
    }
    return o;
  }
  var timer=null;
  function push(){
    if(timer) clearTimeout(timer);
    timer=setTimeout(function(){
      var ts=Date.now();
      try{
        fetch(API,{method:"POST",headers:{"Content-Type":"application/json"},
          body:JSON.stringify({ts:ts,data:snap()})})
          .then(function(r){return r.ok?r.json():null;})
          .then(function(j){ if(j&&j.ok){ try{ localStorage.setItem(TS,String(j.ts||ts)); }catch(e){} } })
          .catch(function(){});
      }catch(e){}
    },600);
  }
  var S=Storage.prototype, oSet=S.setItem, oDel=S.removeItem;
  S.setItem=function(k,v){ oSet.call(this,k,v); if(syncKey(k)) push(); };
  S.removeItem=function(k){ oDel.call(this,k); if(syncKey(k)) push(); };

  function pull(){
    try{
      fetch(API,{headers:{"Accept":"application/json"}})
        .then(function(r){return r.ok?r.json():null;})
        .then(function(j){
          if(!j||!j.data) return;
          var local=Number(localStorage.getItem(TS)||0);
          if((j.ts||0)<=local){ push(); return; }   /* 本地更新，推给服务端 */
          var changed=false;
          for(var k in j.data){
            if(localStorage.getItem(k)!==j.data[k]){ oSet.call(localStorage,k,j.data[k]); changed=true; }
          }
          oSet.call(localStorage,TS,String(j.ts||0));
          if(changed && !sessionStorage.getItem("__cp_reloaded")){
            sessionStorage.setItem("__cp_reloaded","1"); location.reload();
          }
        }).catch(function(){});
    }catch(e){}
  }
  if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",pull);
  else pull();
})();
</script>
"""


def inject(path):
    s = io.open(path, "r", encoding="utf-8", newline="").read()
    if '__cp_ts' in s:
        print("skip (已注入):", path)
        return
    i = s.index("<style")
    s = s[:i] + SHIM + "\n" + s[i:]
    io.open(path, "w", encoding="utf-8", newline="").write(s)
    print("injected:", path, len(s))


if __name__ == "__main__":
    for f in sys.argv[1:]:
        inject(f)
