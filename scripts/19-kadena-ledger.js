const P=require('/Users/tadeaskmenta/repos/balance-checker/node_modules/pact-lang-api');
const t=()=>Math.round(Date.now()/1000)-60;
const num=d=>(d==null?0:(typeof d==='number'?d:(d.decimal!==undefined?parseFloat(d.decimal):(d.int!==undefined?parseFloat(d.int):0))));
const code=`(fold (+) 0.0 (map (lambda (k) (at 'balance (read runonflux.flux.ledger k))) (keys runonflux.flux.ledger)))`;
(async()=>{
 let grand=0, rows=0;
 for(let c=0;c<20;c++){
  const API=`https://api.chainweb-community.org/chainweb/0.0/mainnet01/chain/${c}/pact`;
  const meta=P.lang.mkMeta('dummyaccount',String(c),0.00000001,500000,t(),900);
  try{
   const n=await P.fetch.local({pactCode:'(length (keys runonflux.flux.ledger))',keyPairs:P.crypto.genKeyPair(),meta},API);
   if(n.result.status!=='success'){console.log(`chain ${c}: no module`);continue;}
   const cnt=num(n.result.data);
   const r=await P.fetch.local({pactCode:code,keyPairs:P.crypto.genKeyPair(),meta},API);
   if(r.result.status==='success'){const v=num(r.result.data);grand+=v;rows+=cnt;
     console.log(`chain ${String(c).padStart(2)}: accounts ${String(cnt).padStart(6)}  supply ${v}`);}
   else console.log(`chain ${c}: accounts ${cnt} SUM FAILED ${String(r.result.error&&r.result.error.message).slice(0,70)}`);
  }catch(e){console.log(`chain ${c}: ERR ${String(e).slice(0,60)}`);}
 }
 console.log('TOTAL accounts:',rows,' TOTAL supply:',grand);
})();
