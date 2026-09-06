const P=require('/Users/tadeaskmenta/repos/balance-checker/node_modules/pact-lang-api');
const t=()=>Math.round(Date.now()/1000)-60;
const num=d=>(d==null?0:(typeof d==='number'?d:(d.decimal!==undefined?parseFloat(d.decimal):(d.int!==undefined?parseFloat(d.int):0))));
const accts=[['SNAPSHOT','fluxsnapshotreward'],['MINING','fluxcoinbasereward'],['SWAP','fluxswap'],
 ['LOCKED','k:869daee30836deb4beb5fefcffb53bcb92d44514670bc721c073065b5832dbfb'],
 ['LOCKED SNAPSHOT','k:e7f86a71fd26282cc7818f034ed7ab169effef724e06b31632b7be0f808c5b6e'],
 ['LOCKED MINING','k:52638422aa11e81e1098da69a0cb3bbcb676294efa3d000a7bec80e8e946d0b1']];
(async()=>{let grand=0;
 for(const c of [0,1,2,3]){
  const API=`https://api.chainweb-community.org/chainweb/0.0/mainnet01/chain/${c}/pact`;
  const meta=P.lang.mkMeta('dummyaccount',String(c),0.00000001,6000,t(),900);
  let sub=0;
  for(const [l,a] of accts){
   try{const r=await P.fetch.local({pactCode:`(runonflux.flux.get-balance "${a}")`,keyPairs:P.crypto.genKeyPair(),meta},API);
    if(r.result.status==='success'){const v=num(r.result.data);sub+=v;if(v)console.log(`  chain ${c} ${l.padEnd(16)} ${v}`);}
   }catch(e){}
  }
  grand+=sub; console.log(`chain ${c} issuer-held: ${sub}`);
 }
 console.log('ISSUER-HELD TOTAL:',grand);
 console.log('TOTAL SUPPLY:',39998820.80974744);
 console.log('OUTSTANDING:',39998820.80974744-grand);
})();
