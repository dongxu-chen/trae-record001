(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const s of document.querySelectorAll('link[rel="modulepreload"]'))n(s);new MutationObserver(s=>{for(const r of s)if(r.type==="childList")for(const o of r.addedNodes)o.tagName==="LINK"&&o.rel==="modulepreload"&&n(o)}).observe(document,{childList:!0,subtree:!0});function t(s){const r={};return s.integrity&&(r.integrity=s.integrity),s.referrerPolicy&&(r.referrerPolicy=s.referrerPolicy),s.crossOrigin==="use-credentials"?r.credentials="include":s.crossOrigin==="anonymous"?r.credentials="omit":r.credentials="same-origin",r}function n(s){if(s.ep)return;s.ep=!0;const r=t(s);fetch(s.href,r)}})();/**
* @vue/shared v3.5.34
* (c) 2018-present Yuxi (Evan) You and Vue contributors
* @license MIT
**/function au(i){const e=Object.create(null);for(const t of i.split(","))e[t]=1;return t=>t in e}const ht={},mr=[],ri=()=>{},Id=()=>!1,el=i=>i.charCodeAt(0)===111&&i.charCodeAt(1)===110&&(i.charCodeAt(2)>122||i.charCodeAt(2)<97),tl=i=>i.startsWith("onUpdate:"),Kt=Object.assign,lu=(i,e)=>{const t=i.indexOf(e);t>-1&&i.splice(t,1)},A_=Object.prototype.hasOwnProperty,st=(i,e)=>A_.call(i,e),ze=Array.isArray,_r=i=>Po(i)==="[object Map]",nl=i=>Po(i)==="[object Set]",rf=i=>Po(i)==="[object Date]",We=i=>typeof i=="function",bt=i=>typeof i=="string",oi=i=>typeof i=="symbol",ct=i=>i!==null&&typeof i=="object",Od=i=>(ct(i)||We(i))&&We(i.then)&&We(i.catch),Nd=Object.prototype.toString,Po=i=>Nd.call(i),w_=i=>Po(i).slice(8,-1),Fd=i=>Po(i)==="[object Object]",cu=i=>bt(i)&&i!=="NaN"&&i[0]!=="-"&&""+parseInt(i,10)===i,to=au(",key,ref,ref_for,ref_key,onVnodeBeforeMount,onVnodeMounted,onVnodeBeforeUpdate,onVnodeUpdated,onVnodeBeforeUnmount,onVnodeUnmounted"),il=i=>{const e=Object.create(null);return t=>e[t]||(e[t]=i(t))},R_=/-\w/g,qn=il(i=>i.replace(R_,e=>e.slice(1).toUpperCase())),C_=/\B([A-Z])/g,Vs=il(i=>i.replace(C_,"-$1").toLowerCase()),zd=il(i=>i.charAt(0).toUpperCase()+i.slice(1)),wl=il(i=>i?`on${zd(i)}`:""),ni=(i,e)=>!Object.is(i,e),Ea=(i,...e)=>{for(let t=0;t<i.length;t++)i[t](...e)},Bd=(i,e,t,n=!1)=>{Object.defineProperty(i,e,{configurable:!0,enumerable:!1,writable:n,value:t})},sl=i=>{const e=parseFloat(i);return isNaN(e)?i:e};let of;const rl=()=>of||(of=typeof globalThis<"u"?globalThis:typeof self<"u"?self:typeof window<"u"?window:typeof global<"u"?global:{});function gr(i){if(ze(i)){const e={};for(let t=0;t<i.length;t++){const n=i[t],s=bt(n)?U_(n):gr(n);if(s)for(const r in s)e[r]=s[r]}return e}else if(bt(i)||ct(i))return i}const P_=/;(?![^(]*\))/g,L_=/:([^]+)/,D_=/\/\*[^]*?\*\//g;function U_(i){const e={};return i.replace(D_,"").split(P_).forEach(t=>{if(t){const n=t.split(L_);n.length>1&&(e[n[0].trim()]=n[1].trim())}}),e}function en(i){let e="";if(bt(i))e=i;else if(ze(i))for(let t=0;t<i.length;t++){const n=en(i[t]);n&&(e+=n+" ")}else if(ct(i))for(const t in i)i[t]&&(e+=t+" ");return e.trim()}const I_="itemscope,allowfullscreen,formnovalidate,ismap,nomodule,novalidate,readonly",O_=au(I_);function kd(i){return!!i||i===""}function N_(i,e){if(i.length!==e.length)return!1;let t=!0;for(let n=0;t&&n<i.length;n++)t=Lo(i[n],e[n]);return t}function Lo(i,e){if(i===e)return!0;let t=rf(i),n=rf(e);if(t||n)return t&&n?i.getTime()===e.getTime():!1;if(t=oi(i),n=oi(e),t||n)return i===e;if(t=ze(i),n=ze(e),t||n)return t&&n?N_(i,e):!1;if(t=ct(i),n=ct(e),t||n){if(!t||!n)return!1;const s=Object.keys(i).length,r=Object.keys(e).length;if(s!==r)return!1;for(const o in i){const a=i.hasOwnProperty(o),l=e.hasOwnProperty(o);if(a&&!l||!a&&l||!Lo(i[o],e[o]))return!1}}return String(i)===String(e)}function F_(i,e){return i.findIndex(t=>Lo(t,e))}const Vd=i=>!!(i&&i.__v_isRef===!0),Fe=i=>bt(i)?i:i==null?"":ze(i)||ct(i)&&(i.toString===Nd||!We(i.toString))?Vd(i)?Fe(i.value):JSON.stringify(i,Hd,2):String(i),Hd=(i,e)=>Vd(e)?Hd(i,e.value):_r(e)?{[`Map(${e.size})`]:[...e.entries()].reduce((t,[n,s],r)=>(t[Rl(n,r)+" =>"]=s,t),{})}:nl(e)?{[`Set(${e.size})`]:[...e.values()].map(t=>Rl(t))}:oi(e)?Rl(e):ct(e)&&!ze(e)&&!Fd(e)?String(e):e,Rl=(i,e="")=>{var t;return oi(i)?`Symbol(${(t=i.description)!=null?t:e})`:i};/**
* @vue/reactivity v3.5.34
* (c) 2018-present Yuxi (Evan) You and Vue contributors
* @license MIT
**/let Bt;class z_{constructor(e=!1){this.detached=e,this._active=!0,this._on=0,this.effects=[],this.cleanups=[],this._isPaused=!1,this._warnOnRun=!0,this.__v_skip=!0,!e&&Bt&&(Bt.active?(this.parent=Bt,this.index=(Bt.scopes||(Bt.scopes=[])).push(this)-1):(this._active=!1,this._warnOnRun=!1))}get active(){return this._active}pause(){if(this._active){this._isPaused=!0;let e,t;if(this.scopes)for(e=0,t=this.scopes.length;e<t;e++)this.scopes[e].pause();for(e=0,t=this.effects.length;e<t;e++)this.effects[e].pause()}}resume(){if(this._active&&this._isPaused){this._isPaused=!1;let e,t;if(this.scopes)for(e=0,t=this.scopes.length;e<t;e++)this.scopes[e].resume();for(e=0,t=this.effects.length;e<t;e++)this.effects[e].resume()}}run(e){if(this._active){const t=Bt;try{return Bt=this,e()}finally{Bt=t}}}on(){++this._on===1&&(this.prevScope=Bt,Bt=this)}off(){if(this._on>0&&--this._on===0){if(Bt===this)Bt=this.prevScope;else{let e=Bt;for(;e;){if(e.prevScope===this){e.prevScope=this.prevScope;break}e=e.prevScope}}this.prevScope=void 0}}stop(e){if(this._active){this._active=!1;let t,n;for(t=0,n=this.effects.length;t<n;t++)this.effects[t].stop();for(this.effects.length=0,t=0,n=this.cleanups.length;t<n;t++)this.cleanups[t]();if(this.cleanups.length=0,this.scopes){for(t=0,n=this.scopes.length;t<n;t++)this.scopes[t].stop(!0);this.scopes.length=0}if(!this.detached&&this.parent&&!e){const s=this.parent.scopes.pop();s&&s!==this&&(this.parent.scopes[this.index]=s,s.index=this.index)}this.parent=void 0}}}function B_(){return Bt}let pt;const Cl=new WeakSet;class Gd{constructor(e){this.fn=e,this.deps=void 0,this.depsTail=void 0,this.flags=5,this.next=void 0,this.cleanup=void 0,this.scheduler=void 0,Bt&&(Bt.active?Bt.effects.push(this):this.flags&=-2)}pause(){this.flags|=64}resume(){this.flags&64&&(this.flags&=-65,Cl.has(this)&&(Cl.delete(this),this.trigger()))}notify(){this.flags&2&&!(this.flags&32)||this.flags&8||Xd(this)}run(){if(!(this.flags&1))return this.fn();this.flags|=2,af(this),qd(this);const e=pt,t=Yn;pt=this,Yn=!0;try{return this.fn()}finally{Yd(this),pt=e,Yn=t,this.flags&=-3}}stop(){if(this.flags&1){for(let e=this.deps;e;e=e.nextDep)hu(e);this.deps=this.depsTail=void 0,af(this),this.onStop&&this.onStop(),this.flags&=-2}}trigger(){this.flags&64?Cl.add(this):this.scheduler?this.scheduler():this.runIfDirty()}runIfDirty(){Ec(this)&&this.run()}get dirty(){return Ec(this)}}let Wd=0,no,io;function Xd(i,e=!1){if(i.flags|=8,e){i.next=io,io=i;return}i.next=no,no=i}function uu(){Wd++}function fu(){if(--Wd>0)return;if(io){let e=io;for(io=void 0;e;){const t=e.next;e.next=void 0,e.flags&=-9,e=t}}let i;for(;no;){let e=no;for(no=void 0;e;){const t=e.next;if(e.next=void 0,e.flags&=-9,e.flags&1)try{e.trigger()}catch(n){i||(i=n)}e=t}}if(i)throw i}function qd(i){for(let e=i.deps;e;e=e.nextDep)e.version=-1,e.prevActiveLink=e.dep.activeLink,e.dep.activeLink=e}function Yd(i){let e,t=i.depsTail,n=t;for(;n;){const s=n.prevDep;n.version===-1?(n===t&&(t=s),hu(n),k_(n)):e=n,n.dep.activeLink=n.prevActiveLink,n.prevActiveLink=void 0,n=s}i.deps=e,i.depsTail=t}function Ec(i){for(let e=i.deps;e;e=e.nextDep)if(e.dep.version!==e.version||e.dep.computed&&($d(e.dep.computed)||e.dep.version!==e.version))return!0;return!!i._dirty}function $d(i){if(i.flags&4&&!(i.flags&16)||(i.flags&=-17,i.globalVersion===mo)||(i.globalVersion=mo,!i.isSSR&&i.flags&128&&(!i.deps&&!i._dirty||!Ec(i))))return;i.flags|=2;const e=i.dep,t=pt,n=Yn;pt=i,Yn=!0;try{qd(i);const s=i.fn(i._value);(e.version===0||ni(s,i._value))&&(i.flags|=128,i._value=s,e.version++)}catch(s){throw e.version++,s}finally{pt=t,Yn=n,Yd(i),i.flags&=-3}}function hu(i,e=!1){const{dep:t,prevSub:n,nextSub:s}=i;if(n&&(n.nextSub=s,i.prevSub=void 0),s&&(s.prevSub=n,i.nextSub=void 0),t.subs===i&&(t.subs=n,!n&&t.computed)){t.computed.flags&=-5;for(let r=t.computed.deps;r;r=r.nextDep)hu(r,!0)}!e&&!--t.sc&&t.map&&t.map.delete(t.key)}function k_(i){const{prevDep:e,nextDep:t}=i;e&&(e.nextDep=t,i.prevDep=void 0),t&&(t.prevDep=e,i.nextDep=void 0)}let Yn=!0;const jd=[];function Ci(){jd.push(Yn),Yn=!1}function Pi(){const i=jd.pop();Yn=i===void 0?!0:i}function af(i){const{cleanup:e}=i;if(i.cleanup=void 0,e){const t=pt;pt=void 0;try{e()}finally{pt=t}}}let mo=0;class V_{constructor(e,t){this.sub=e,this.dep=t,this.version=t.version,this.nextDep=this.prevDep=this.nextSub=this.prevSub=this.prevActiveLink=void 0}}class du{constructor(e){this.computed=e,this.version=0,this.activeLink=void 0,this.subs=void 0,this.map=void 0,this.key=void 0,this.sc=0,this.__v_skip=!0}track(e){if(!pt||!Yn||pt===this.computed)return;let t=this.activeLink;if(t===void 0||t.sub!==pt)t=this.activeLink=new V_(pt,this),pt.deps?(t.prevDep=pt.depsTail,pt.depsTail.nextDep=t,pt.depsTail=t):pt.deps=pt.depsTail=t,Kd(t);else if(t.version===-1&&(t.version=this.version,t.nextDep)){const n=t.nextDep;n.prevDep=t.prevDep,t.prevDep&&(t.prevDep.nextDep=n),t.prevDep=pt.depsTail,t.nextDep=void 0,pt.depsTail.nextDep=t,pt.depsTail=t,pt.deps===t&&(pt.deps=n)}return t}trigger(e){this.version++,mo++,this.notify(e)}notify(e){uu();try{for(let t=this.subs;t;t=t.prevSub)t.sub.notify()&&t.sub.dep.notify()}finally{fu()}}}function Kd(i){if(i.dep.sc++,i.sub.flags&4){const e=i.dep.computed;if(e&&!i.dep.subs){e.flags|=20;for(let n=e.deps;n;n=n.nextDep)Kd(n)}const t=i.dep.subs;t!==i&&(i.prevSub=t,t&&(t.nextSub=i)),i.dep.subs=i}}const bc=new WeakMap,Cs=Symbol(""),Tc=Symbol(""),_o=Symbol("");function qt(i,e,t){if(Yn&&pt){let n=bc.get(i);n||bc.set(i,n=new Map);let s=n.get(t);s||(n.set(t,s=new du),s.map=n,s.key=t),s.track()}}function Ei(i,e,t,n,s,r){const o=bc.get(i);if(!o){mo++;return}const a=l=>{l&&l.trigger()};if(uu(),e==="clear")o.forEach(a);else{const l=ze(i),c=l&&cu(t);if(l&&t==="length"){const u=Number(n);o.forEach((f,h)=>{(h==="length"||h===_o||!oi(h)&&h>=u)&&a(f)})}else switch((t!==void 0||o.has(void 0))&&a(o.get(t)),c&&a(o.get(_o)),e){case"add":l?c&&a(o.get("length")):(a(o.get(Cs)),_r(i)&&a(o.get(Tc)));break;case"delete":l||(a(o.get(Cs)),_r(i)&&a(o.get(Tc)));break;case"set":_r(i)&&a(o.get(Cs));break}}fu()}function Ws(i){const e=it(i);return e===i?e:(qt(e,"iterate",_o),zn(i)?e:e.map($n))}function ol(i){return qt(i=it(i),"iterate",_o),i}function Qn(i,e){return Li(i)?Ar(Ps(i)?$n(e):e):$n(e)}const H_={__proto__:null,[Symbol.iterator](){return Pl(this,Symbol.iterator,i=>Qn(this,i))},concat(...i){return Ws(this).concat(...i.map(e=>ze(e)?Ws(e):e))},entries(){return Pl(this,"entries",i=>(i[1]=Qn(this,i[1]),i))},every(i,e){return ui(this,"every",i,e,void 0,arguments)},filter(i,e){return ui(this,"filter",i,e,t=>t.map(n=>Qn(this,n)),arguments)},find(i,e){return ui(this,"find",i,e,t=>Qn(this,t),arguments)},findIndex(i,e){return ui(this,"findIndex",i,e,void 0,arguments)},findLast(i,e){return ui(this,"findLast",i,e,t=>Qn(this,t),arguments)},findLastIndex(i,e){return ui(this,"findLastIndex",i,e,void 0,arguments)},forEach(i,e){return ui(this,"forEach",i,e,void 0,arguments)},includes(...i){return Ll(this,"includes",i)},indexOf(...i){return Ll(this,"indexOf",i)},join(i){return Ws(this).join(i)},lastIndexOf(...i){return Ll(this,"lastIndexOf",i)},map(i,e){return ui(this,"map",i,e,void 0,arguments)},pop(){return Vr(this,"pop")},push(...i){return Vr(this,"push",i)},reduce(i,...e){return lf(this,"reduce",i,e)},reduceRight(i,...e){return lf(this,"reduceRight",i,e)},shift(){return Vr(this,"shift")},some(i,e){return ui(this,"some",i,e,void 0,arguments)},splice(...i){return Vr(this,"splice",i)},toReversed(){return Ws(this).toReversed()},toSorted(i){return Ws(this).toSorted(i)},toSpliced(...i){return Ws(this).toSpliced(...i)},unshift(...i){return Vr(this,"unshift",i)},values(){return Pl(this,"values",i=>Qn(this,i))}};function Pl(i,e,t){const n=ol(i),s=n[e]();return n!==i&&!zn(i)&&(s._next=s.next,s.next=()=>{const r=s._next();return r.done||(r.value=t(r.value)),r}),s}const G_=Array.prototype;function ui(i,e,t,n,s,r){const o=ol(i),a=o!==i&&!zn(i),l=o[e];if(l!==G_[e]){const f=l.apply(i,r);return a?$n(f):f}let c=t;o!==i&&(a?c=function(f,h){return t.call(this,Qn(i,f),h,i)}:t.length>2&&(c=function(f,h){return t.call(this,f,h,i)}));const u=l.call(o,c,n);return a&&s?s(u):u}function lf(i,e,t,n){const s=ol(i),r=s!==i&&!zn(i);let o=t,a=!1;s!==i&&(r?(a=n.length===0,o=function(c,u,f){return a&&(a=!1,c=Qn(i,c)),t.call(this,c,Qn(i,u),f,i)}):t.length>3&&(o=function(c,u,f){return t.call(this,c,u,f,i)}));const l=s[e](o,...n);return a?Qn(i,l):l}function Ll(i,e,t){const n=it(i);qt(n,"iterate",_o);const s=n[e](...t);return(s===-1||s===!1)&&_u(t[0])?(t[0]=it(t[0]),n[e](...t)):s}function Vr(i,e,t=[]){Ci(),uu();const n=it(i)[e].apply(i,t);return fu(),Pi(),n}const W_=au("__proto__,__v_isRef,__isVue"),Zd=new Set(Object.getOwnPropertyNames(Symbol).filter(i=>i!=="arguments"&&i!=="caller").map(i=>Symbol[i]).filter(oi));function X_(i){oi(i)||(i=String(i));const e=it(this);return qt(e,"has",i),e.hasOwnProperty(i)}class Jd{constructor(e=!1,t=!1){this._isReadonly=e,this._isShallow=t}get(e,t,n){if(t==="__v_skip")return e.__v_skip;const s=this._isReadonly,r=this._isShallow;if(t==="__v_isReactive")return!s;if(t==="__v_isReadonly")return s;if(t==="__v_isShallow")return r;if(t==="__v_raw")return n===(s?r?tg:np:r?tp:ep).get(e)||Object.getPrototypeOf(e)===Object.getPrototypeOf(n)?e:void 0;const o=ze(e);if(!s){let l;if(o&&(l=H_[t]))return l;if(t==="hasOwnProperty")return X_}const a=Reflect.get(e,t,$t(e)?e:n);if((oi(t)?Zd.has(t):W_(t))||(s||qt(e,"get",t),r))return a;if($t(a)){const l=o&&cu(t)?a:a.value;return s&&ct(l)?wc(l):l}return ct(a)?s?wc(a):al(a):a}}class Qd extends Jd{constructor(e=!1){super(!1,e)}set(e,t,n,s){let r=e[t];const o=ze(e)&&cu(t);if(!this._isShallow){const c=Li(r);if(!zn(n)&&!Li(n)&&(r=it(r),n=it(n)),!o&&$t(r)&&!$t(n))return c||(r.value=n),!0}const a=o?Number(t)<e.length:st(e,t),l=Reflect.set(e,t,n,$t(e)?e:s);return e===it(s)&&(a?ni(n,r)&&Ei(e,"set",t,n):Ei(e,"add",t,n)),l}deleteProperty(e,t){const n=st(e,t);e[t];const s=Reflect.deleteProperty(e,t);return s&&n&&Ei(e,"delete",t,void 0),s}has(e,t){const n=Reflect.has(e,t);return(!oi(t)||!Zd.has(t))&&qt(e,"has",t),n}ownKeys(e){return qt(e,"iterate",ze(e)?"length":Cs),Reflect.ownKeys(e)}}class q_ extends Jd{constructor(e=!1){super(!0,e)}set(e,t){return!0}deleteProperty(e,t){return!0}}const Y_=new Qd,$_=new q_,j_=new Qd(!0);const Ac=i=>i,Go=i=>Reflect.getPrototypeOf(i);function K_(i,e,t){return function(...n){const s=this.__v_raw,r=it(s),o=_r(r),a=i==="entries"||i===Symbol.iterator&&o,l=i==="keys"&&o,c=s[i](...n),u=t?Ac:e?Ar:$n;return!e&&qt(r,"iterate",l?Tc:Cs),Kt(Object.create(c),{next(){const{value:f,done:h}=c.next();return h?{value:f,done:h}:{value:a?[u(f[0]),u(f[1])]:u(f),done:h}}})}}function Wo(i){return function(...e){return i==="delete"?!1:i==="clear"?void 0:this}}function Z_(i,e){const t={get(s){const r=this.__v_raw,o=it(r),a=it(s);i||(ni(s,a)&&qt(o,"get",s),qt(o,"get",a));const{has:l}=Go(o),c=e?Ac:i?Ar:$n;if(l.call(o,s))return c(r.get(s));if(l.call(o,a))return c(r.get(a));r!==o&&r.get(s)},get size(){const s=this.__v_raw;return!i&&qt(it(s),"iterate",Cs),s.size},has(s){const r=this.__v_raw,o=it(r),a=it(s);return i||(ni(s,a)&&qt(o,"has",s),qt(o,"has",a)),s===a?r.has(s):r.has(s)||r.has(a)},forEach(s,r){const o=this,a=o.__v_raw,l=it(a),c=e?Ac:i?Ar:$n;return!i&&qt(l,"iterate",Cs),a.forEach((u,f)=>s.call(r,c(u),c(f),o))}};return Kt(t,i?{add:Wo("add"),set:Wo("set"),delete:Wo("delete"),clear:Wo("clear")}:{add(s){const r=it(this),o=Go(r),a=it(s),l=!e&&!zn(s)&&!Li(s)?a:s;return o.has.call(r,l)||ni(s,l)&&o.has.call(r,s)||ni(a,l)&&o.has.call(r,a)||(r.add(l),Ei(r,"add",l,l)),this},set(s,r){!e&&!zn(r)&&!Li(r)&&(r=it(r));const o=it(this),{has:a,get:l}=Go(o);let c=a.call(o,s);c||(s=it(s),c=a.call(o,s));const u=l.call(o,s);return o.set(s,r),c?ni(r,u)&&Ei(o,"set",s,r):Ei(o,"add",s,r),this},delete(s){const r=it(this),{has:o,get:a}=Go(r);let l=o.call(r,s);l||(s=it(s),l=o.call(r,s)),a&&a.call(r,s);const c=r.delete(s);return l&&Ei(r,"delete",s,void 0),c},clear(){const s=it(this),r=s.size!==0,o=s.clear();return r&&Ei(s,"clear",void 0,void 0),o}}),["keys","values","entries",Symbol.iterator].forEach(s=>{t[s]=K_(s,i,e)}),t}function pu(i,e){const t=Z_(i,e);return(n,s,r)=>s==="__v_isReactive"?!i:s==="__v_isReadonly"?i:s==="__v_raw"?n:Reflect.get(st(t,s)&&s in n?t:n,s,r)}const J_={get:pu(!1,!1)},Q_={get:pu(!1,!0)},eg={get:pu(!0,!1)};const ep=new WeakMap,tp=new WeakMap,np=new WeakMap,tg=new WeakMap;function ng(i){switch(i){case"Object":case"Array":return 1;case"Map":case"Set":case"WeakMap":case"WeakSet":return 2;default:return 0}}function ig(i){return i.__v_skip||!Object.isExtensible(i)?0:ng(w_(i))}function al(i){return Li(i)?i:mu(i,!1,Y_,J_,ep)}function sg(i){return mu(i,!1,j_,Q_,tp)}function wc(i){return mu(i,!0,$_,eg,np)}function mu(i,e,t,n,s){if(!ct(i)||i.__v_raw&&!(e&&i.__v_isReactive))return i;const r=ig(i);if(r===0)return i;const o=s.get(i);if(o)return o;const a=new Proxy(i,r===2?n:t);return s.set(i,a),a}function Ps(i){return Li(i)?Ps(i.__v_raw):!!(i&&i.__v_isReactive)}function Li(i){return!!(i&&i.__v_isReadonly)}function zn(i){return!!(i&&i.__v_isShallow)}function _u(i){return i?!!i.__v_raw:!1}function it(i){const e=i&&i.__v_raw;return e?it(e):i}function rg(i){return!st(i,"__v_skip")&&Object.isExtensible(i)&&Bd(i,"__v_skip",!0),i}const $n=i=>ct(i)?al(i):i,Ar=i=>ct(i)?wc(i):i;function $t(i){return i?i.__v_isRef===!0:!1}function tt(i){return og(i,!1)}function og(i,e){return $t(i)?i:new ag(i,e)}class ag{constructor(e,t){this.dep=new du,this.__v_isRef=!0,this.__v_isShallow=!1,this._rawValue=t?e:it(e),this._value=t?e:$n(e),this.__v_isShallow=t}get value(){return this.dep.track(),this._value}set value(e){const t=this._rawValue,n=this.__v_isShallow||zn(e)||Li(e);e=n?e:it(e),ni(e,t)&&(this._rawValue=e,this._value=n?e:$n(e),this.dep.trigger())}}function gu(i){return $t(i)?i.value:i}const lg={get:(i,e,t)=>e==="__v_raw"?i:gu(Reflect.get(i,e,t)),set:(i,e,t,n)=>{const s=i[e];return $t(s)&&!$t(t)?(s.value=t,!0):Reflect.set(i,e,t,n)}};function ip(i){return Ps(i)?i:new Proxy(i,lg)}class cg{constructor(e,t,n){this.fn=e,this.setter=t,this._value=void 0,this.dep=new du(this),this.__v_isRef=!0,this.deps=void 0,this.depsTail=void 0,this.flags=16,this.globalVersion=mo-1,this.next=void 0,this.effect=this,this.__v_isReadonly=!t,this.isSSR=n}notify(){if(this.flags|=16,!(this.flags&8)&&pt!==this)return Xd(this,!0),!0}get value(){const e=this.dep.track();return $d(this),e&&(e.version=this.dep.version),this._value}set value(e){this.setter&&this.setter(e)}}function ug(i,e,t=!1){let n,s;return We(i)?n=i:(n=i.get,s=i.set),new cg(n,s,t)}const Xo={},La=new WeakMap;let Ss;function fg(i,e=!1,t=Ss){if(t){let n=La.get(t);n||La.set(t,n=[]),n.push(i)}}function hg(i,e,t=ht){const{immediate:n,deep:s,once:r,scheduler:o,augmentJob:a,call:l}=t,c=S=>s?S:zn(S)||s===!1||s===0?bi(S,1):bi(S);let u,f,h,d,g=!1,_=!1;if($t(i)?(f=()=>i.value,g=zn(i)):Ps(i)?(f=()=>c(i),g=!0):ze(i)?(_=!0,g=i.some(S=>Ps(S)||zn(S)),f=()=>i.map(S=>{if($t(S))return S.value;if(Ps(S))return c(S);if(We(S))return l?l(S,2):S()})):We(i)?e?f=l?()=>l(i,2):i:f=()=>{if(h){Ci();try{h()}finally{Pi()}}const S=Ss;Ss=u;try{return l?l(i,3,[d]):i(d)}finally{Ss=S}}:f=ri,e&&s){const S=f,R=s===!0?1/0:s;f=()=>bi(S(),R)}const m=B_(),p=()=>{u.stop(),m&&m.active&&lu(m.effects,u)};if(r&&e){const S=e;e=(...R)=>{S(...R),p()}}let x=_?new Array(i.length).fill(Xo):Xo;const y=S=>{if(!(!(u.flags&1)||!u.dirty&&!S))if(e){const R=u.run();if(s||g||(_?R.some((L,w)=>ni(L,x[w])):ni(R,x))){h&&h();const L=Ss;Ss=u;try{const w=[R,x===Xo?void 0:_&&x[0]===Xo?[]:x,d];x=R,l?l(e,3,w):e(...w)}finally{Ss=L}}}else u.run()};return a&&a(y),u=new Gd(f),u.scheduler=o?()=>o(y,!1):y,d=S=>fg(S,!1,u),h=u.onStop=()=>{const S=La.get(u);if(S){if(l)l(S,4);else for(const R of S)R();La.delete(u)}},e?n?y(!0):x=u.run():o?o(y.bind(null,!0),!0):u.run(),p.pause=u.pause.bind(u),p.resume=u.resume.bind(u),p.stop=p,p}function bi(i,e=1/0,t){if(e<=0||!ct(i)||i.__v_skip||(t=t||new Map,(t.get(i)||0)>=e))return i;if(t.set(i,e),e--,$t(i))bi(i.value,e,t);else if(ze(i))for(let n=0;n<i.length;n++)bi(i[n],e,t);else if(nl(i)||_r(i))i.forEach(n=>{bi(n,e,t)});else if(Fd(i)){for(const n in i)bi(i[n],e,t);for(const n of Object.getOwnPropertySymbols(i))Object.prototype.propertyIsEnumerable.call(i,n)&&bi(i[n],e,t)}return i}/**
* @vue/runtime-core v3.5.34
* (c) 2018-present Yuxi (Evan) You and Vue contributors
* @license MIT
**/function Do(i,e,t,n){try{return n?i(...n):i()}catch(s){ll(s,e,t)}}function ai(i,e,t,n){if(We(i)){const s=Do(i,e,t,n);return s&&Od(s)&&s.catch(r=>{ll(r,e,t)}),s}if(ze(i)){const s=[];for(let r=0;r<i.length;r++)s.push(ai(i[r],e,t,n));return s}}function ll(i,e,t,n=!0){const s=e?e.vnode:null,{errorHandler:r,throwUnhandledErrorInProduction:o}=e&&e.appContext.config||ht;if(e){let a=e.parent;const l=e.proxy,c=`https://vuejs.org/error-reference/#runtime-${t}`;for(;a;){const u=a.ec;if(u){for(let f=0;f<u.length;f++)if(u[f](i,l,c)===!1)return}a=a.parent}if(r){Ci(),Do(r,null,10,[i,l,c]),Pi();return}}dg(i,t,s,n,o)}function dg(i,e,t,n=!0,s=!1){if(s)throw i;console.error(i)}const nn=[];let Zn=-1;const vr=[];let Gi=null,ur=0;const sp=Promise.resolve();let Da=null;function rp(i){const e=Da||sp;return i?e.then(this?i.bind(this):i):e}function pg(i){let e=Zn+1,t=nn.length;for(;e<t;){const n=e+t>>>1,s=nn[n],r=go(s);r<i||r===i&&s.flags&2?e=n+1:t=n}return e}function vu(i){if(!(i.flags&1)){const e=go(i),t=nn[nn.length-1];!t||!(i.flags&2)&&e>=go(t)?nn.push(i):nn.splice(pg(e),0,i),i.flags|=1,op()}}function op(){Da||(Da=sp.then(lp))}function mg(i){ze(i)?vr.push(...i):Gi&&i.id===-1?Gi.splice(ur+1,0,i):i.flags&1||(vr.push(i),i.flags|=1),op()}function cf(i,e,t=Zn+1){for(;t<nn.length;t++){const n=nn[t];if(n&&n.flags&2){if(i&&n.id!==i.uid)continue;nn.splice(t,1),t--,n.flags&4&&(n.flags&=-2),n(),n.flags&4||(n.flags&=-2)}}}function ap(i){if(vr.length){const e=[...new Set(vr)].sort((t,n)=>go(t)-go(n));if(vr.length=0,Gi){Gi.push(...e);return}for(Gi=e,ur=0;ur<Gi.length;ur++){const t=Gi[ur];t.flags&4&&(t.flags&=-2),t.flags&8||t(),t.flags&=-2}Gi=null,ur=0}}const go=i=>i.id==null?i.flags&2?-1:1/0:i.id;function lp(i){try{for(Zn=0;Zn<nn.length;Zn++){const e=nn[Zn];e&&!(e.flags&8)&&(e.flags&4&&(e.flags&=-2),Do(e,e.i,e.i?15:14),e.flags&4||(e.flags&=-2))}}finally{for(;Zn<nn.length;Zn++){const e=nn[Zn];e&&(e.flags&=-2)}Zn=-1,nn.length=0,ap(),Da=null,(nn.length||vr.length)&&lp()}}let On=null,cp=null;function Ua(i){const e=On;return On=i,cp=i&&i.type.__scopeId||null,e}function _g(i,e=On,t){if(!e||i._n)return i;const n=(...s)=>{n._d&&yf(-1);const r=Ua(e);let o;try{o=i(...s)}finally{Ua(r),n._d&&yf(1)}return o};return n._n=!0,n._c=!0,n._d=!0,n}function $e(i,e){if(On===null)return i;const t=dl(On),n=i.dirs||(i.dirs=[]);for(let s=0;s<e.length;s++){let[r,o,a,l=ht]=e[s];r&&(We(r)&&(r={mounted:r,updated:r}),r.deep&&bi(o),n.push({dir:r,instance:t,value:o,oldValue:void 0,arg:a,modifiers:l}))}return i}function hs(i,e,t,n){const s=i.dirs,r=e&&e.dirs;for(let o=0;o<s.length;o++){const a=s[o];r&&(a.oldValue=r[o].value);let l=a.dir[n];l&&(Ci(),ai(l,t,8,[i.el,a,i,e]),Pi())}}function gg(i,e){if(rn){let t=rn.provides;const n=rn.parent&&rn.parent.provides;n===t&&(t=rn.provides=Object.create(n)),t[i]=e}}function ba(i,e,t=!1){const n=_0();if(n||yr){let s=yr?yr._context.provides:n?n.parent==null||n.ce?n.vnode.appContext&&n.vnode.appContext.provides:n.parent.provides:void 0;if(s&&i in s)return s[i];if(arguments.length>1)return t&&We(e)?e.call(n&&n.proxy):e}}const vg=Symbol.for("v-scx"),xg=()=>ba(vg);function xr(i,e,t){return up(i,e,t)}function up(i,e,t=ht){const{immediate:n,deep:s,flush:r,once:o}=t,a=Kt({},t),l=e&&n||!e&&r!=="post";let c;if(xo){if(r==="sync"){const d=xg();c=d.__watcherHandles||(d.__watcherHandles=[])}else if(!l){const d=()=>{};return d.stop=ri,d.resume=ri,d.pause=ri,d}}const u=rn;a.call=(d,g,_)=>ai(d,u,g,_);let f=!1;r==="post"?a.scheduler=d=>{an(d,u&&u.suspense)}:r!=="sync"&&(f=!0,a.scheduler=(d,g)=>{g?d():vu(d)}),a.augmentJob=d=>{e&&(d.flags|=4),f&&(d.flags|=2,u&&(d.id=u.uid,d.i=u))};const h=hg(i,e,a);return xo&&(c?c.push(h):l&&h()),h}function yg(i,e,t){const n=this.proxy,s=bt(i)?i.includes(".")?fp(n,i):()=>n[i]:i.bind(n,n);let r;We(e)?r=e:(r=e.handler,t=e);const o=Uo(this),a=up(s,r.bind(n),t);return o(),a}function fp(i,e){const t=e.split(".");return()=>{let n=i;for(let s=0;s<t.length&&n;s++)n=n[t[s]];return n}}const Sg=Symbol("_vte"),Mg=i=>i.__isTeleport,Eg=Symbol("_leaveCb");function xu(i,e){i.shapeFlag&6&&i.component?(i.transition=e,xu(i.component.subTree,e)):i.shapeFlag&128?(i.ssContent.transition=e.clone(i.ssContent),i.ssFallback.transition=e.clone(i.ssFallback)):i.transition=e}function hp(i){i.ids=[i.ids[0]+i.ids[2]+++"-",0,0]}function uf(i,e){let t;return!!((t=Object.getOwnPropertyDescriptor(i,e))&&!t.configurable)}const Ia=new WeakMap;function so(i,e,t,n,s=!1){if(ze(i)){i.forEach((_,m)=>so(_,e&&(ze(e)?e[m]:e),t,n,s));return}if(ro(n)&&!s){n.shapeFlag&512&&n.type.__asyncResolved&&n.component.subTree.component&&so(i,e,t,n.component.subTree);return}const r=n.shapeFlag&4?dl(n.component):n.el,o=s?null:r,{i:a,r:l}=i,c=e&&e.r,u=a.refs===ht?a.refs={}:a.refs,f=a.setupState,h=it(f),d=f===ht?Id:_=>uf(u,_)?!1:st(h,_),g=(_,m)=>!(m&&uf(u,m));if(c!=null&&c!==l){if(ff(e),bt(c))u[c]=null,d(c)&&(f[c]=null);else if($t(c)){const _=e;g(c,_.k)&&(c.value=null),_.k&&(u[_.k]=null)}}if(We(l))Do(l,a,12,[o,u]);else{const _=bt(l),m=$t(l);if(_||m){const p=()=>{if(i.f){const x=_?d(l)?f[l]:u[l]:g()||!i.k?l.value:u[i.k];if(s)ze(x)&&lu(x,r);else if(ze(x))x.includes(r)||x.push(r);else if(_)u[l]=[r],d(l)&&(f[l]=u[l]);else{const y=[r];g(l,i.k)&&(l.value=y),i.k&&(u[i.k]=y)}}else _?(u[l]=o,d(l)&&(f[l]=o)):m&&(g(l,i.k)&&(l.value=o),i.k&&(u[i.k]=o))};if(o){const x=()=>{p(),Ia.delete(i)};x.id=-1,Ia.set(i,x),an(x,t)}else ff(i),p()}}}function ff(i){const e=Ia.get(i);e&&(e.flags|=8,Ia.delete(i))}rl().requestIdleCallback;rl().cancelIdleCallback;const ro=i=>!!i.type.__asyncLoader,dp=i=>i.type.__isKeepAlive;function bg(i,e){pp(i,"a",e)}function Tg(i,e){pp(i,"da",e)}function pp(i,e,t=rn){const n=i.__wdc||(i.__wdc=()=>{let s=t;for(;s;){if(s.isDeactivated)return;s=s.parent}return i()});if(cl(e,n,t),t){let s=t.parent;for(;s&&s.parent;)dp(s.parent.vnode)&&Ag(n,e,t,s),s=s.parent}}function Ag(i,e,t,n){const s=cl(e,i,n,!0);ul(()=>{lu(n[e],s)},t)}function cl(i,e,t=rn,n=!1){if(t){const s=t[i]||(t[i]=[]),r=e.__weh||(e.__weh=(...o)=>{Ci();const a=Uo(t),l=ai(e,t,i,o);return a(),Pi(),l});return n?s.unshift(r):s.push(r),r}}const Oi=i=>(e,t=rn)=>{(!xo||i==="sp")&&cl(i,(...n)=>e(...n),t)},wg=Oi("bm"),yu=Oi("m"),Rg=Oi("bu"),Cg=Oi("u"),Pg=Oi("bum"),ul=Oi("um"),Lg=Oi("sp"),Dg=Oi("rtg"),Ug=Oi("rtc");function Ig(i,e=rn){cl("ec",i,e)}const Og=Symbol.for("v-ndc");function Ti(i,e,t,n){let s;const r=t,o=ze(i);if(o||bt(i)){const a=o&&Ps(i);let l=!1,c=!1;a&&(l=!zn(i),c=Li(i),i=ol(i)),s=new Array(i.length);for(let u=0,f=i.length;u<f;u++)s[u]=e(l?c?Ar($n(i[u])):$n(i[u]):i[u],u,void 0,r)}else if(typeof i=="number"){s=new Array(i);for(let a=0;a<i;a++)s[a]=e(a+1,a,void 0,r)}else if(ct(i))if(i[Symbol.iterator])s=Array.from(i,(a,l)=>e(a,l,void 0,r));else{const a=Object.keys(i);s=new Array(a.length);for(let l=0,c=a.length;l<c;l++){const u=a[l];s[l]=e(i[u],u,l,r)}}else s=[];return s}const Rc=i=>i?Op(i)?dl(i):Rc(i.parent):null,oo=Kt(Object.create(null),{$:i=>i,$el:i=>i.vnode.el,$data:i=>i.data,$props:i=>i.props,$attrs:i=>i.attrs,$slots:i=>i.slots,$refs:i=>i.refs,$parent:i=>Rc(i.parent),$root:i=>Rc(i.root),$host:i=>i.ce,$emit:i=>i.emit,$options:i=>_p(i),$forceUpdate:i=>i.f||(i.f=()=>{vu(i.update)}),$nextTick:i=>i.n||(i.n=rp.bind(i.proxy)),$watch:i=>yg.bind(i)}),Dl=(i,e)=>i!==ht&&!i.__isScriptSetup&&st(i,e),Ng={get({_:i},e){if(e==="__v_skip")return!0;const{ctx:t,setupState:n,data:s,props:r,accessCache:o,type:a,appContext:l}=i;if(e[0]!=="$"){const h=o[e];if(h!==void 0)switch(h){case 1:return n[e];case 2:return s[e];case 4:return t[e];case 3:return r[e]}else{if(Dl(n,e))return o[e]=1,n[e];if(s!==ht&&st(s,e))return o[e]=2,s[e];if(st(r,e))return o[e]=3,r[e];if(t!==ht&&st(t,e))return o[e]=4,t[e];Cc&&(o[e]=0)}}const c=oo[e];let u,f;if(c)return e==="$attrs"&&qt(i.attrs,"get",""),c(i);if((u=a.__cssModules)&&(u=u[e]))return u;if(t!==ht&&st(t,e))return o[e]=4,t[e];if(f=l.config.globalProperties,st(f,e))return f[e]},set({_:i},e,t){const{data:n,setupState:s,ctx:r}=i;return Dl(s,e)?(s[e]=t,!0):n!==ht&&st(n,e)?(n[e]=t,!0):st(i.props,e)||e[0]==="$"&&e.slice(1)in i?!1:(r[e]=t,!0)},has({_:{data:i,setupState:e,accessCache:t,ctx:n,appContext:s,props:r,type:o}},a){let l;return!!(t[a]||i!==ht&&a[0]!=="$"&&st(i,a)||Dl(e,a)||st(r,a)||st(n,a)||st(oo,a)||st(s.config.globalProperties,a)||(l=o.__cssModules)&&l[a])},defineProperty(i,e,t){return t.get!=null?i._.accessCache[e]=0:st(t,"value")&&this.set(i,e,t.value,null),Reflect.defineProperty(i,e,t)}};function hf(i){return ze(i)?i.reduce((e,t)=>(e[t]=null,e),{}):i}let Cc=!0;function Fg(i){const e=_p(i),t=i.proxy,n=i.ctx;Cc=!1,e.beforeCreate&&df(e.beforeCreate,i,"bc");const{data:s,computed:r,methods:o,watch:a,provide:l,inject:c,created:u,beforeMount:f,mounted:h,beforeUpdate:d,updated:g,activated:_,deactivated:m,beforeDestroy:p,beforeUnmount:x,destroyed:y,unmounted:S,render:R,renderTracked:L,renderTriggered:w,errorCaptured:B,serverPrefetch:v,expose:b,inheritAttrs:N,components:A,directives:I,filters:O}=e;if(c&&zg(c,n,null),o)for(const q in o){const Z=o[q];We(Z)&&(n[q]=Z.bind(t))}if(s){const q=s.call(t,t);ct(q)&&(i.data=al(q))}if(Cc=!0,r)for(const q in r){const Z=r[q],W=We(Z)?Z.bind(t,t):We(Z.get)?Z.get.bind(t,t):ri,j=!We(Z)&&We(Z.set)?Z.set.bind(t):ri,G=lo({get:W,set:j});Object.defineProperty(n,q,{enumerable:!0,configurable:!0,get:()=>G.value,set:re=>G.value=re})}if(a)for(const q in a)mp(a[q],n,t,q);if(l){const q=We(l)?l.call(t):l;Reflect.ownKeys(q).forEach(Z=>{gg(Z,q[Z])})}u&&df(u,i,"c");function H(q,Z){ze(Z)?Z.forEach(W=>q(W.bind(t))):Z&&q(Z.bind(t))}if(H(wg,f),H(yu,h),H(Rg,d),H(Cg,g),H(bg,_),H(Tg,m),H(Ig,B),H(Ug,L),H(Dg,w),H(Pg,x),H(ul,S),H(Lg,v),ze(b))if(b.length){const q=i.exposed||(i.exposed={});b.forEach(Z=>{Object.defineProperty(q,Z,{get:()=>t[Z],set:W=>t[Z]=W,enumerable:!0})})}else i.exposed||(i.exposed={});R&&i.render===ri&&(i.render=R),N!=null&&(i.inheritAttrs=N),A&&(i.components=A),I&&(i.directives=I),v&&hp(i)}function zg(i,e,t=ri){ze(i)&&(i=Pc(i));for(const n in i){const s=i[n];let r;ct(s)?"default"in s?r=ba(s.from||n,s.default,!0):r=ba(s.from||n):r=ba(s),$t(r)?Object.defineProperty(e,n,{enumerable:!0,configurable:!0,get:()=>r.value,set:o=>r.value=o}):e[n]=r}}function df(i,e,t){ai(ze(i)?i.map(n=>n.bind(e.proxy)):i.bind(e.proxy),e,t)}function mp(i,e,t,n){let s=n.includes(".")?fp(t,n):()=>t[n];if(bt(i)){const r=e[i];We(r)&&xr(s,r)}else if(We(i))xr(s,i.bind(t));else if(ct(i))if(ze(i))i.forEach(r=>mp(r,e,t,n));else{const r=We(i.handler)?i.handler.bind(t):e[i.handler];We(r)&&xr(s,r,i)}}function _p(i){const e=i.type,{mixins:t,extends:n}=e,{mixins:s,optionsCache:r,config:{optionMergeStrategies:o}}=i.appContext,a=r.get(e);let l;return a?l=a:!s.length&&!t&&!n?l=e:(l={},s.length&&s.forEach(c=>Oa(l,c,o,!0)),Oa(l,e,o)),ct(e)&&r.set(e,l),l}function Oa(i,e,t,n=!1){const{mixins:s,extends:r}=e;r&&Oa(i,r,t,!0),s&&s.forEach(o=>Oa(i,o,t,!0));for(const o in e)if(!(n&&o==="expose")){const a=Bg[o]||t&&t[o];i[o]=a?a(i[o],e[o]):e[o]}return i}const Bg={data:pf,props:mf,emits:mf,methods:Zr,computed:Zr,beforeCreate:Jt,created:Jt,beforeMount:Jt,mounted:Jt,beforeUpdate:Jt,updated:Jt,beforeDestroy:Jt,beforeUnmount:Jt,destroyed:Jt,unmounted:Jt,activated:Jt,deactivated:Jt,errorCaptured:Jt,serverPrefetch:Jt,components:Zr,directives:Zr,watch:Vg,provide:pf,inject:kg};function pf(i,e){return e?i?function(){return Kt(We(i)?i.call(this,this):i,We(e)?e.call(this,this):e)}:e:i}function kg(i,e){return Zr(Pc(i),Pc(e))}function Pc(i){if(ze(i)){const e={};for(let t=0;t<i.length;t++)e[i[t]]=i[t];return e}return i}function Jt(i,e){return i?[...new Set([].concat(i,e))]:e}function Zr(i,e){return i?Kt(Object.create(null),i,e):e}function mf(i,e){return i?ze(i)&&ze(e)?[...new Set([...i,...e])]:Kt(Object.create(null),hf(i),hf(e??{})):e}function Vg(i,e){if(!i)return e;if(!e)return i;const t=Kt(Object.create(null),i);for(const n in e)t[n]=Jt(i[n],e[n]);return t}function gp(){return{app:null,config:{isNativeTag:Id,performance:!1,globalProperties:{},optionMergeStrategies:{},errorHandler:void 0,warnHandler:void 0,compilerOptions:{}},mixins:[],components:{},directives:{},provides:Object.create(null),optionsCache:new WeakMap,propsCache:new WeakMap,emitsCache:new WeakMap}}let Hg=0;function Gg(i,e){return function(n,s=null){We(n)||(n=Kt({},n)),s!=null&&!ct(s)&&(s=null);const r=gp(),o=new WeakSet,a=[];let l=!1;const c=r.app={_uid:Hg++,_component:n,_props:s,_container:null,_context:r,_instance:null,version:M0,get config(){return r.config},set config(u){},use(u,...f){return o.has(u)||(u&&We(u.install)?(o.add(u),u.install(c,...f)):We(u)&&(o.add(u),u(c,...f))),c},mixin(u){return r.mixins.includes(u)||r.mixins.push(u),c},component(u,f){return f?(r.components[u]=f,c):r.components[u]},directive(u,f){return f?(r.directives[u]=f,c):r.directives[u]},mount(u,f,h){if(!l){const d=c._ceVNode||bn(n,s);return d.appContext=r,h===!0?h="svg":h===!1&&(h=void 0),i(d,u,h),l=!0,c._container=u,u.__vue_app__=c,dl(d.component)}},onUnmount(u){a.push(u)},unmount(){l&&(ai(a,c._instance,16),i(null,c._container),delete c._container.__vue_app__)},provide(u,f){return r.provides[u]=f,c},runWithContext(u){const f=yr;yr=c;try{return u()}finally{yr=f}}};return c}}let yr=null;const Wg=(i,e)=>e==="modelValue"||e==="model-value"?i.modelModifiers:i[`${e}Modifiers`]||i[`${qn(e)}Modifiers`]||i[`${Vs(e)}Modifiers`];function Xg(i,e,...t){if(i.isUnmounted)return;const n=i.vnode.props||ht;let s=t;const r=e.startsWith("update:"),o=r&&Wg(n,e.slice(7));o&&(o.trim&&(s=t.map(u=>bt(u)?u.trim():u)),o.number&&(s=t.map(sl)));let a,l=n[a=wl(e)]||n[a=wl(qn(e))];!l&&r&&(l=n[a=wl(Vs(e))]),l&&ai(l,i,6,s);const c=n[a+"Once"];if(c){if(!i.emitted)i.emitted={};else if(i.emitted[a])return;i.emitted[a]=!0,ai(c,i,6,s)}}const qg=new WeakMap;function vp(i,e,t=!1){const n=t?qg:e.emitsCache,s=n.get(i);if(s!==void 0)return s;const r=i.emits;let o={},a=!1;if(!We(i)){const l=c=>{const u=vp(c,e,!0);u&&(a=!0,Kt(o,u))};!t&&e.mixins.length&&e.mixins.forEach(l),i.extends&&l(i.extends),i.mixins&&i.mixins.forEach(l)}return!r&&!a?(ct(i)&&n.set(i,null),null):(ze(r)?r.forEach(l=>o[l]=null):Kt(o,r),ct(i)&&n.set(i,o),o)}function fl(i,e){return!i||!el(e)?!1:(e=e.slice(2).replace(/Once$/,""),st(i,e[0].toLowerCase()+e.slice(1))||st(i,Vs(e))||st(i,e))}function _f(i){const{type:e,vnode:t,proxy:n,withProxy:s,propsOptions:[r],slots:o,attrs:a,emit:l,render:c,renderCache:u,props:f,data:h,setupState:d,ctx:g,inheritAttrs:_}=i,m=Ua(i);let p,x;try{if(t.shapeFlag&4){const S=s||n,R=S;p=ei(c.call(R,S,u,f,d,h,g)),x=a}else{const S=e;p=ei(S.length>1?S(f,{attrs:a,slots:o,emit:l}):S(f,null)),x=e.props?a:Yg(a)}}catch(S){ao.length=0,ll(S,i,1),p=bn(is)}let y=p;if(x&&_!==!1){const S=Object.keys(x),{shapeFlag:R}=y;S.length&&R&7&&(r&&S.some(tl)&&(x=$g(x,r)),y=wr(y,x,!1,!0))}return t.dirs&&(y=wr(y,null,!1,!0),y.dirs=y.dirs?y.dirs.concat(t.dirs):t.dirs),t.transition&&xu(y,t.transition),p=y,Ua(m),p}const Yg=i=>{let e;for(const t in i)(t==="class"||t==="style"||el(t))&&((e||(e={}))[t]=i[t]);return e},$g=(i,e)=>{const t={};for(const n in i)(!tl(n)||!(n.slice(9)in e))&&(t[n]=i[n]);return t};function jg(i,e,t){const{props:n,children:s,component:r}=i,{props:o,children:a,patchFlag:l}=e,c=r.emitsOptions;if(e.dirs||e.transition)return!0;if(t&&l>=0){if(l&1024)return!0;if(l&16)return n?gf(n,o,c):!!o;if(l&8){const u=e.dynamicProps;for(let f=0;f<u.length;f++){const h=u[f];if(xp(o,n,h)&&!fl(c,h))return!0}}}else return(s||a)&&(!a||!a.$stable)?!0:n===o?!1:n?o?gf(n,o,c):!0:!!o;return!1}function gf(i,e,t){const n=Object.keys(e);if(n.length!==Object.keys(i).length)return!0;for(let s=0;s<n.length;s++){const r=n[s];if(xp(e,i,r)&&!fl(t,r))return!0}return!1}function xp(i,e,t){const n=i[t],s=e[t];return t==="style"&&ct(n)&&ct(s)?!Lo(n,s):n!==s}function Kg({vnode:i,parent:e,suspense:t},n){for(;e;){const s=e.subTree;if(s.suspense&&s.suspense.activeBranch===i&&(s.suspense.vnode.el=s.el=n,i=s),s===i)(i=e.vnode).el=n,e=e.parent;else break}t&&t.activeBranch===i&&(t.vnode.el=n)}const yp={},Sp=()=>Object.create(yp),Mp=i=>Object.getPrototypeOf(i)===yp;function Zg(i,e,t,n=!1){const s={},r=Sp();i.propsDefaults=Object.create(null),Ep(i,e,s,r);for(const o in i.propsOptions[0])o in s||(s[o]=void 0);t?i.props=n?s:sg(s):i.type.props?i.props=s:i.props=r,i.attrs=r}function Jg(i,e,t,n){const{props:s,attrs:r,vnode:{patchFlag:o}}=i,a=it(s),[l]=i.propsOptions;let c=!1;if((n||o>0)&&!(o&16)){if(o&8){const u=i.vnode.dynamicProps;for(let f=0;f<u.length;f++){let h=u[f];if(fl(i.emitsOptions,h))continue;const d=e[h];if(l)if(st(r,h))d!==r[h]&&(r[h]=d,c=!0);else{const g=qn(h);s[g]=Lc(l,a,g,d,i,!1)}else d!==r[h]&&(r[h]=d,c=!0)}}}else{Ep(i,e,s,r)&&(c=!0);let u;for(const f in a)(!e||!st(e,f)&&((u=Vs(f))===f||!st(e,u)))&&(l?t&&(t[f]!==void 0||t[u]!==void 0)&&(s[f]=Lc(l,a,f,void 0,i,!0)):delete s[f]);if(r!==a)for(const f in r)(!e||!st(e,f))&&(delete r[f],c=!0)}c&&Ei(i.attrs,"set","")}function Ep(i,e,t,n){const[s,r]=i.propsOptions;let o=!1,a;if(e)for(let l in e){if(to(l))continue;const c=e[l];let u;s&&st(s,u=qn(l))?!r||!r.includes(u)?t[u]=c:(a||(a={}))[u]=c:fl(i.emitsOptions,l)||(!(l in n)||c!==n[l])&&(n[l]=c,o=!0)}if(r){const l=it(t),c=a||ht;for(let u=0;u<r.length;u++){const f=r[u];t[f]=Lc(s,l,f,c[f],i,!st(c,f))}}return o}function Lc(i,e,t,n,s,r){const o=i[t];if(o!=null){const a=st(o,"default");if(a&&n===void 0){const l=o.default;if(o.type!==Function&&!o.skipFactory&&We(l)){const{propsDefaults:c}=s;if(t in c)n=c[t];else{const u=Uo(s);n=c[t]=l.call(null,e),u()}}else n=l;s.ce&&s.ce._setProp(t,n)}o[0]&&(r&&!a?n=!1:o[1]&&(n===""||n===Vs(t))&&(n=!0))}return n}const Qg=new WeakMap;function bp(i,e,t=!1){const n=t?Qg:e.propsCache,s=n.get(i);if(s)return s;const r=i.props,o={},a=[];let l=!1;if(!We(i)){const u=f=>{l=!0;const[h,d]=bp(f,e,!0);Kt(o,h),d&&a.push(...d)};!t&&e.mixins.length&&e.mixins.forEach(u),i.extends&&u(i.extends),i.mixins&&i.mixins.forEach(u)}if(!r&&!l)return ct(i)&&n.set(i,mr),mr;if(ze(r))for(let u=0;u<r.length;u++){const f=qn(r[u]);vf(f)&&(o[f]=ht)}else if(r)for(const u in r){const f=qn(u);if(vf(f)){const h=r[u],d=o[f]=ze(h)||We(h)?{type:h}:Kt({},h),g=d.type;let _=!1,m=!0;if(ze(g))for(let p=0;p<g.length;++p){const x=g[p],y=We(x)&&x.name;if(y==="Boolean"){_=!0;break}else y==="String"&&(m=!1)}else _=We(g)&&g.name==="Boolean";d[0]=_,d[1]=m,(_||st(d,"default"))&&a.push(f)}}const c=[o,a];return ct(i)&&n.set(i,c),c}function vf(i){return i[0]!=="$"&&!to(i)}const Su=i=>i==="_"||i==="_ctx"||i==="$stable",Mu=i=>ze(i)?i.map(ei):[ei(i)],e0=(i,e,t)=>{if(e._n)return e;const n=_g((...s)=>Mu(e(...s)),t);return n._c=!1,n},Tp=(i,e,t)=>{const n=i._ctx;for(const s in i){if(Su(s))continue;const r=i[s];if(We(r))e[s]=e0(s,r,n);else if(r!=null){const o=Mu(r);e[s]=()=>o}}},Ap=(i,e)=>{const t=Mu(e);i.slots.default=()=>t},wp=(i,e,t)=>{for(const n in e)(t||!Su(n))&&(i[n]=e[n])},t0=(i,e,t)=>{const n=i.slots=Sp();if(i.vnode.shapeFlag&32){const s=e._;s?(wp(n,e,t),t&&Bd(n,"_",s,!0)):Tp(e,n)}else e&&Ap(i,e)},n0=(i,e,t)=>{const{vnode:n,slots:s}=i;let r=!0,o=ht;if(n.shapeFlag&32){const a=e._;a?t&&a===1?r=!1:wp(s,e,t):(r=!e.$stable,Tp(e,s)),o=e}else e&&(Ap(i,e),o={default:1});if(r)for(const a in s)!Su(a)&&o[a]==null&&delete s[a]},an=a0;function i0(i){return s0(i)}function s0(i,e){const t=rl();t.__VUE__=!0;const{insert:n,remove:s,patchProp:r,createElement:o,createText:a,createComment:l,setText:c,setElementText:u,parentNode:f,nextSibling:h,setScopeId:d=ri,insertStaticContent:g}=i,_=(E,z,V,te=null,K=null,oe=null,ae=void 0,T=null,M=!!z.dynamicChildren)=>{if(E===z)return;E&&!Hr(E,z)&&(te=Te(E),re(E,K,oe,!0),E=null),z.patchFlag===-2&&(M=!1,z.dynamicChildren=null);const{type:U,ref:ee,shapeFlag:X}=z;switch(U){case hl:m(E,z,V,te);break;case is:p(E,z,V,te);break;case Il:E==null&&x(z,V,te,ae);break;case Nt:A(E,z,V,te,K,oe,ae,T,M);break;default:X&1?R(E,z,V,te,K,oe,ae,T,M):X&6?I(E,z,V,te,K,oe,ae,T,M):(X&64||X&128)&&U.process(E,z,V,te,K,oe,ae,T,M,Se)}ee!=null&&K?so(ee,E&&E.ref,oe,z||E,!z):ee==null&&E&&E.ref!=null&&so(E.ref,null,oe,E,!0)},m=(E,z,V,te)=>{if(E==null)n(z.el=a(z.children),V,te);else{const K=z.el=E.el;z.children!==E.children&&c(K,z.children)}},p=(E,z,V,te)=>{E==null?n(z.el=l(z.children||""),V,te):z.el=E.el},x=(E,z,V,te)=>{[E.el,E.anchor]=g(E.children,z,V,te,E.el,E.anchor)},y=({el:E,anchor:z},V,te)=>{let K;for(;E&&E!==z;)K=h(E),n(E,V,te),E=K;n(z,V,te)},S=({el:E,anchor:z})=>{let V;for(;E&&E!==z;)V=h(E),s(E),E=V;s(z)},R=(E,z,V,te,K,oe,ae,T,M)=>{if(z.type==="svg"?ae="svg":z.type==="math"&&(ae="mathml"),E==null)L(z,V,te,K,oe,ae,T,M);else{const U=E.el&&E.el._isVueCE?E.el:null;try{U&&U._beginPatch(),v(E,z,K,oe,ae,T,M)}finally{U&&U._endPatch()}}},L=(E,z,V,te,K,oe,ae,T)=>{let M,U;const{props:ee,shapeFlag:X,transition:J,dirs:fe}=E;if(M=E.el=o(E.type,oe,ee&&ee.is,ee),X&8?u(M,E.children):X&16&&B(E.children,M,null,te,K,Ul(E,oe),ae,T),fe&&hs(E,null,te,"created"),w(M,E,E.scopeId,ae,te),ee){for(const de in ee)de!=="value"&&!to(de)&&r(M,de,null,ee[de],oe,te);"value"in ee&&r(M,"value",null,ee.value,oe),(U=ee.onVnodeBeforeMount)&&Kn(U,te,E)}fe&&hs(E,null,te,"beforeMount");const ue=r0(K,J);ue&&J.beforeEnter(M),n(M,z,V),((U=ee&&ee.onVnodeMounted)||ue||fe)&&an(()=>{try{U&&Kn(U,te,E),ue&&J.enter(M),fe&&hs(E,null,te,"mounted")}finally{}},K)},w=(E,z,V,te,K)=>{if(V&&d(E,V),te)for(let oe=0;oe<te.length;oe++)d(E,te[oe]);if(K){let oe=K.subTree;if(z===oe||Lp(oe.type)&&(oe.ssContent===z||oe.ssFallback===z)){const ae=K.vnode;w(E,ae,ae.scopeId,ae.slotScopeIds,K.parent)}}},B=(E,z,V,te,K,oe,ae,T,M=0)=>{for(let U=M;U<E.length;U++){const ee=E[U]=T?yi(E[U]):ei(E[U]);_(null,ee,z,V,te,K,oe,ae,T)}},v=(E,z,V,te,K,oe,ae)=>{const T=z.el=E.el;let{patchFlag:M,dynamicChildren:U,dirs:ee}=z;M|=E.patchFlag&16;const X=E.props||ht,J=z.props||ht;let fe;if(V&&ds(V,!1),(fe=J.onVnodeBeforeUpdate)&&Kn(fe,V,z,E),ee&&hs(z,E,V,"beforeUpdate"),V&&ds(V,!0),(X.innerHTML&&J.innerHTML==null||X.textContent&&J.textContent==null)&&u(T,""),U?b(E.dynamicChildren,U,T,V,te,Ul(z,K),oe):ae||Z(E,z,T,null,V,te,Ul(z,K),oe,!1),M>0){if(M&16)N(T,X,J,V,K);else if(M&2&&X.class!==J.class&&r(T,"class",null,J.class,K),M&4&&r(T,"style",X.style,J.style,K),M&8){const ue=z.dynamicProps;for(let de=0;de<ue.length;de++){const xe=ue[de],Ae=X[xe],ce=J[xe];(ce!==Ae||xe==="value")&&r(T,xe,Ae,ce,K,V)}}M&1&&E.children!==z.children&&u(T,z.children)}else!ae&&U==null&&N(T,X,J,V,K);((fe=J.onVnodeUpdated)||ee)&&an(()=>{fe&&Kn(fe,V,z,E),ee&&hs(z,E,V,"updated")},te)},b=(E,z,V,te,K,oe,ae)=>{for(let T=0;T<z.length;T++){const M=E[T],U=z[T],ee=M.el&&(M.type===Nt||!Hr(M,U)||M.shapeFlag&198)?f(M.el):V;_(M,U,ee,null,te,K,oe,ae,!0)}},N=(E,z,V,te,K)=>{if(z!==V){if(z!==ht)for(const oe in z)!to(oe)&&!(oe in V)&&r(E,oe,z[oe],null,K,te);for(const oe in V){if(to(oe))continue;const ae=V[oe],T=z[oe];ae!==T&&oe!=="value"&&r(E,oe,T,ae,K,te)}"value"in V&&r(E,"value",z.value,V.value,K)}},A=(E,z,V,te,K,oe,ae,T,M)=>{const U=z.el=E?E.el:a(""),ee=z.anchor=E?E.anchor:a("");let{patchFlag:X,dynamicChildren:J,slotScopeIds:fe}=z;fe&&(T=T?T.concat(fe):fe),E==null?(n(U,V,te),n(ee,V,te),B(z.children||[],V,ee,K,oe,ae,T,M)):X>0&&X&64&&J&&E.dynamicChildren&&E.dynamicChildren.length===J.length?(b(E.dynamicChildren,J,V,K,oe,ae,T),(z.key!=null||K&&z===K.subTree)&&Rp(E,z,!0)):Z(E,z,V,ee,K,oe,ae,T,M)},I=(E,z,V,te,K,oe,ae,T,M)=>{z.slotScopeIds=T,E==null?z.shapeFlag&512?K.ctx.activate(z,V,te,ae,M):O(z,V,te,K,oe,ae,M):k(E,z,M)},O=(E,z,V,te,K,oe,ae)=>{const T=E.component=m0(E,te,K);if(dp(E)&&(T.ctx.renderer=Se),g0(T,!1,ae),T.asyncDep){if(K&&K.registerDep(T,H,ae),!E.el){const M=T.subTree=bn(is);p(null,M,z,V),E.placeholder=M.el}}else H(T,E,z,V,K,oe,ae)},k=(E,z,V)=>{const te=z.component=E.component;if(jg(E,z,V))if(te.asyncDep&&!te.asyncResolved){q(te,z,V);return}else te.next=z,te.update();else z.el=E.el,te.vnode=z},H=(E,z,V,te,K,oe,ae)=>{const T=()=>{if(E.isMounted){let{next:X,bu:J,u:fe,parent:ue,vnode:de}=E;{const De=Cp(E);if(De){X&&(X.el=de.el,q(E,X,ae)),De.asyncDep.then(()=>{an(()=>{E.isUnmounted||U()},K)});return}}let xe=X,Ae;ds(E,!1),X?(X.el=de.el,q(E,X,ae)):X=de,J&&Ea(J),(Ae=X.props&&X.props.onVnodeBeforeUpdate)&&Kn(Ae,ue,X,de),ds(E,!0);const ce=_f(E),ke=E.subTree;E.subTree=ce,_(ke,ce,f(ke.el),Te(ke),E,K,oe),X.el=ce.el,xe===null&&Kg(E,ce.el),fe&&an(fe,K),(Ae=X.props&&X.props.onVnodeUpdated)&&an(()=>Kn(Ae,ue,X,de),K)}else{let X;const{el:J,props:fe}=z,{bm:ue,m:de,parent:xe,root:Ae,type:ce}=E,ke=ro(z);ds(E,!1),ue&&Ea(ue),!ke&&(X=fe&&fe.onVnodeBeforeMount)&&Kn(X,xe,z),ds(E,!0);{Ae.ce&&Ae.ce._hasShadowRoot()&&Ae.ce._injectChildStyle(ce,E.parent?E.parent.type:void 0);const De=E.subTree=_f(E);_(null,De,V,te,E,K,oe),z.el=De.el}if(de&&an(de,K),!ke&&(X=fe&&fe.onVnodeMounted)){const De=z;an(()=>Kn(X,xe,De),K)}(z.shapeFlag&256||xe&&ro(xe.vnode)&&xe.vnode.shapeFlag&256)&&E.a&&an(E.a,K),E.isMounted=!0,z=V=te=null}};E.scope.on();const M=E.effect=new Gd(T);E.scope.off();const U=E.update=M.run.bind(M),ee=E.job=M.runIfDirty.bind(M);ee.i=E,ee.id=E.uid,M.scheduler=()=>vu(ee),ds(E,!0),U()},q=(E,z,V)=>{z.component=E;const te=E.vnode.props;E.vnode=z,E.next=null,Jg(E,z.props,te,V),n0(E,z.children,V),Ci(),cf(E),Pi()},Z=(E,z,V,te,K,oe,ae,T,M=!1)=>{const U=E&&E.children,ee=E?E.shapeFlag:0,X=z.children,{patchFlag:J,shapeFlag:fe}=z;if(J>0){if(J&128){j(U,X,V,te,K,oe,ae,T,M);return}else if(J&256){W(U,X,V,te,K,oe,ae,T,M);return}}fe&8?(ee&16&&be(U,K,oe),X!==U&&u(V,X)):ee&16?fe&16?j(U,X,V,te,K,oe,ae,T,M):be(U,K,oe,!0):(ee&8&&u(V,""),fe&16&&B(X,V,te,K,oe,ae,T,M))},W=(E,z,V,te,K,oe,ae,T,M)=>{E=E||mr,z=z||mr;const U=E.length,ee=z.length,X=Math.min(U,ee);let J;for(J=0;J<X;J++){const fe=z[J]=M?yi(z[J]):ei(z[J]);_(E[J],fe,V,null,K,oe,ae,T,M)}U>ee?be(E,K,oe,!0,!1,X):B(z,V,te,K,oe,ae,T,M,X)},j=(E,z,V,te,K,oe,ae,T,M)=>{let U=0;const ee=z.length;let X=E.length-1,J=ee-1;for(;U<=X&&U<=J;){const fe=E[U],ue=z[U]=M?yi(z[U]):ei(z[U]);if(Hr(fe,ue))_(fe,ue,V,null,K,oe,ae,T,M);else break;U++}for(;U<=X&&U<=J;){const fe=E[X],ue=z[J]=M?yi(z[J]):ei(z[J]);if(Hr(fe,ue))_(fe,ue,V,null,K,oe,ae,T,M);else break;X--,J--}if(U>X){if(U<=J){const fe=J+1,ue=fe<ee?z[fe].el:te;for(;U<=J;)_(null,z[U]=M?yi(z[U]):ei(z[U]),V,ue,K,oe,ae,T,M),U++}}else if(U>J)for(;U<=X;)re(E[U],K,oe,!0),U++;else{const fe=U,ue=U,de=new Map;for(U=ue;U<=J;U++){const ge=z[U]=M?yi(z[U]):ei(z[U]);ge.key!=null&&de.set(ge.key,U)}let xe,Ae=0;const ce=J-ue+1;let ke=!1,De=0;const Le=new Array(ce);for(U=0;U<ce;U++)Le[U]=0;for(U=fe;U<=X;U++){const ge=E[U];if(Ae>=ce){re(ge,K,oe,!0);continue}let D;if(ge.key!=null)D=de.get(ge.key);else for(xe=ue;xe<=J;xe++)if(Le[xe-ue]===0&&Hr(ge,z[xe])){D=xe;break}D===void 0?re(ge,K,oe,!0):(Le[D-ue]=U+1,D>=De?De=D:ke=!0,_(ge,z[D],V,null,K,oe,ae,T,M),Ae++)}const Re=ke?o0(Le):mr;for(xe=Re.length-1,U=ce-1;U>=0;U--){const ge=ue+U,D=z[ge],pe=z[ge+1],we=ge+1<ee?pe.el||Pp(pe):te;Le[U]===0?_(null,D,V,we,K,oe,ae,T,M):ke&&(xe<0||U!==Re[xe]?G(D,V,we,2):xe--)}}},G=(E,z,V,te,K=null)=>{const{el:oe,type:ae,transition:T,children:M,shapeFlag:U}=E;if(U&6){G(E.component.subTree,z,V,te);return}if(U&128){E.suspense.move(z,V,te);return}if(U&64){ae.move(E,z,V,Se);return}if(ae===Nt){n(oe,z,V);for(let X=0;X<M.length;X++)G(M[X],z,V,te);n(E.anchor,z,V);return}if(ae===Il){y(E,z,V);return}if(te!==2&&U&1&&T)if(te===0)T.beforeEnter(oe),n(oe,z,V),an(()=>T.enter(oe),K);else{const{leave:X,delayLeave:J,afterLeave:fe}=T,ue=()=>{E.ctx.isUnmounted?s(oe):n(oe,z,V)},de=()=>{oe._isLeaving&&oe[Eg](!0),X(oe,()=>{ue(),fe&&fe()})};J?J(oe,ue,de):de()}else n(oe,z,V)},re=(E,z,V,te=!1,K=!1)=>{const{type:oe,props:ae,ref:T,children:M,dynamicChildren:U,shapeFlag:ee,patchFlag:X,dirs:J,cacheIndex:fe,memo:ue}=E;if(X===-2&&(K=!1),T!=null&&(Ci(),so(T,null,V,E,!0),Pi()),fe!=null&&(z.renderCache[fe]=void 0),ee&256){z.ctx.deactivate(E);return}const de=ee&1&&J,xe=!ro(E);let Ae;if(xe&&(Ae=ae&&ae.onVnodeBeforeUnmount)&&Kn(Ae,z,E),ee&6)_e(E.component,V,te);else{if(ee&128){E.suspense.unmount(V,te);return}de&&hs(E,null,z,"beforeUnmount"),ee&64?E.type.remove(E,z,V,Se,te):U&&!U.hasOnce&&(oe!==Nt||X>0&&X&64)?be(U,z,V,!1,!0):(oe===Nt&&X&384||!K&&ee&16)&&be(M,z,V),te&&Q(E)}const ce=ue!=null&&fe==null;(xe&&(Ae=ae&&ae.onVnodeUnmounted)||de||ce)&&an(()=>{Ae&&Kn(Ae,z,E),de&&hs(E,null,z,"unmounted"),ce&&(E.el=null)},V)},Q=E=>{const{type:z,el:V,anchor:te,transition:K}=E;if(z===Nt){le(V,te);return}if(z===Il){S(E);return}const oe=()=>{s(V),K&&!K.persisted&&K.afterLeave&&K.afterLeave()};if(E.shapeFlag&1&&K&&!K.persisted){const{leave:ae,delayLeave:T}=K,M=()=>ae(V,oe);T?T(E.el,oe,M):M()}else oe()},le=(E,z)=>{let V;for(;E!==z;)V=h(E),s(E),E=V;s(z)},_e=(E,z,V)=>{const{bum:te,scope:K,job:oe,subTree:ae,um:T,m:M,a:U}=E;xf(M),xf(U),te&&Ea(te),K.stop(),oe&&(oe.flags|=8,re(ae,E,z,V)),T&&an(T,z),an(()=>{E.isUnmounted=!0},z)},be=(E,z,V,te=!1,K=!1,oe=0)=>{for(let ae=oe;ae<E.length;ae++)re(E[ae],z,V,te,K)},Te=E=>{if(E.shapeFlag&6)return Te(E.component.subTree);if(E.shapeFlag&128)return E.suspense.next();const z=h(E.anchor||E.el),V=z&&z[Sg];return V?h(V):z};let Ue=!1;const Ie=(E,z,V)=>{let te;E==null?z._vnode&&(re(z._vnode,null,null,!0),te=z._vnode.component):_(z._vnode||null,E,z,null,null,null,V),z._vnode=E,Ue||(Ue=!0,cf(te),ap(),Ue=!1)},Se={p:_,um:re,m:G,r:Q,mt:O,mc:B,pc:Z,pbc:b,n:Te,o:i};return{render:Ie,hydrate:void 0,createApp:Gg(Ie)}}function Ul({type:i,props:e},t){return t==="svg"&&i==="foreignObject"||t==="mathml"&&i==="annotation-xml"&&e&&e.encoding&&e.encoding.includes("html")?void 0:t}function ds({effect:i,job:e},t){t?(i.flags|=32,e.flags|=4):(i.flags&=-33,e.flags&=-5)}function r0(i,e){return(!i||i&&!i.pendingBranch)&&e&&!e.persisted}function Rp(i,e,t=!1){const n=i.children,s=e.children;if(ze(n)&&ze(s))for(let r=0;r<n.length;r++){const o=n[r];let a=s[r];a.shapeFlag&1&&!a.dynamicChildren&&((a.patchFlag<=0||a.patchFlag===32)&&(a=s[r]=yi(s[r]),a.el=o.el),!t&&a.patchFlag!==-2&&Rp(o,a)),a.type===hl&&(a.patchFlag===-1&&(a=s[r]=yi(a)),a.el=o.el),a.type===is&&!a.el&&(a.el=o.el)}}function o0(i){const e=i.slice(),t=[0];let n,s,r,o,a;const l=i.length;for(n=0;n<l;n++){const c=i[n];if(c!==0){if(s=t[t.length-1],i[s]<c){e[n]=s,t.push(n);continue}for(r=0,o=t.length-1;r<o;)a=r+o>>1,i[t[a]]<c?r=a+1:o=a;c<i[t[r]]&&(r>0&&(e[n]=t[r-1]),t[r]=n)}}for(r=t.length,o=t[r-1];r-- >0;)t[r]=o,o=e[o];return t}function Cp(i){const e=i.subTree.component;if(e)return e.asyncDep&&!e.asyncResolved?e:Cp(e)}function xf(i){if(i)for(let e=0;e<i.length;e++)i[e].flags|=8}function Pp(i){if(i.placeholder)return i.placeholder;const e=i.component;return e?Pp(e.subTree):null}const Lp=i=>i.__isSuspense;function a0(i,e){e&&e.pendingBranch?ze(i)?e.effects.push(...i):e.effects.push(i):mg(i)}const Nt=Symbol.for("v-fgt"),hl=Symbol.for("v-txt"),is=Symbol.for("v-cmt"),Il=Symbol.for("v-stc"),ao=[];let Sn=null;function rt(i=!1){ao.push(Sn=i?null:[])}function l0(){ao.pop(),Sn=ao[ao.length-1]||null}let vo=1;function yf(i,e=!1){vo+=i,i<0&&Sn&&e&&(Sn.hasOnce=!0)}function Dp(i){return i.dynamicChildren=vo>0?Sn||mr:null,l0(),vo>0&&Sn&&Sn.push(i),i}function lt(i,e,t,n,s,r){return Dp(C(i,e,t,n,s,r,!0))}function c0(i,e,t,n,s){return Dp(bn(i,e,t,n,s,!0))}function Up(i){return i?i.__v_isVNode===!0:!1}function Hr(i,e){return i.type===e.type&&i.key===e.key}const Ip=({key:i})=>i??null,Ta=({ref:i,ref_key:e,ref_for:t})=>(typeof i=="number"&&(i=""+i),i!=null?bt(i)||$t(i)||We(i)?{i:On,r:i,k:e,f:!!t}:i:null);function C(i,e=null,t=null,n=0,s=null,r=i===Nt?0:1,o=!1,a=!1){const l={__v_isVNode:!0,__v_skip:!0,type:i,props:e,key:e&&Ip(e),ref:e&&Ta(e),scopeId:cp,slotScopeIds:null,children:t,component:null,suspense:null,ssContent:null,ssFallback:null,dirs:null,transition:null,el:null,anchor:null,target:null,targetStart:null,targetAnchor:null,staticCount:0,shapeFlag:r,patchFlag:n,dynamicProps:s,dynamicChildren:null,appContext:null,ctx:On};return a?(Eu(l,t),r&128&&i.normalize(l)):t&&(l.shapeFlag|=bt(t)?8:16),vo>0&&!o&&Sn&&(l.patchFlag>0||r&6)&&l.patchFlag!==32&&Sn.push(l),l}const bn=u0;function u0(i,e=null,t=null,n=0,s=null,r=!1){if((!i||i===Og)&&(i=is),Up(i)){const a=wr(i,e,!0);return t&&Eu(a,t),vo>0&&!r&&Sn&&(a.shapeFlag&6?Sn[Sn.indexOf(i)]=a:Sn.push(a)),a.patchFlag=-2,a}if(S0(i)&&(i=i.__vccOpts),e){e=f0(e);let{class:a,style:l}=e;a&&!bt(a)&&(e.class=en(a)),ct(l)&&(_u(l)&&!ze(l)&&(l=Kt({},l)),e.style=gr(l))}const o=bt(i)?1:Lp(i)?128:Mg(i)?64:ct(i)?4:We(i)?2:0;return C(i,e,t,n,s,o,r,!0)}function f0(i){return i?_u(i)||Mp(i)?Kt({},i):i:null}function wr(i,e,t=!1,n=!1){const{props:s,ref:r,patchFlag:o,children:a,transition:l}=i,c=e?h0(s||{},e):s,u={__v_isVNode:!0,__v_skip:!0,type:i.type,props:c,key:c&&Ip(c),ref:e&&e.ref?t&&r?ze(r)?r.concat(Ta(e)):[r,Ta(e)]:Ta(e):r,scopeId:i.scopeId,slotScopeIds:i.slotScopeIds,children:a,target:i.target,targetStart:i.targetStart,targetAnchor:i.targetAnchor,staticCount:i.staticCount,shapeFlag:i.shapeFlag,patchFlag:e&&i.type!==Nt?o===-1?16:o|16:o,dynamicProps:i.dynamicProps,dynamicChildren:i.dynamicChildren,appContext:i.appContext,dirs:i.dirs,transition:l,component:i.component,suspense:i.suspense,ssContent:i.ssContent&&wr(i.ssContent),ssFallback:i.ssFallback&&wr(i.ssFallback),placeholder:i.placeholder,el:i.el,anchor:i.anchor,ctx:i.ctx,ce:i.ce};return l&&n&&xu(u,l.clone(u)),u}function ws(i=" ",e=0){return bn(hl,null,i,e)}function wi(i="",e=!1){return e?(rt(),c0(is,null,i)):bn(is,null,i)}function ei(i){return i==null||typeof i=="boolean"?bn(is):ze(i)?bn(Nt,null,i.slice()):Up(i)?yi(i):bn(hl,null,String(i))}function yi(i){return i.el===null&&i.patchFlag!==-1||i.memo?i:wr(i)}function Eu(i,e){let t=0;const{shapeFlag:n}=i;if(e==null)e=null;else if(ze(e))t=16;else if(typeof e=="object")if(n&65){const s=e.default;s&&(s._c&&(s._d=!1),Eu(i,s()),s._c&&(s._d=!0));return}else{t=32;const s=e._;!s&&!Mp(e)?e._ctx=On:s===3&&On&&(On.slots._===1?e._=1:(e._=2,i.patchFlag|=1024))}else We(e)?(e={default:e,_ctx:On},t=32):(e=String(e),n&64?(t=16,e=[ws(e)]):t=8);i.children=e,i.shapeFlag|=t}function h0(...i){const e={};for(let t=0;t<i.length;t++){const n=i[t];for(const s in n)if(s==="class")e.class!==n.class&&(e.class=en([e.class,n.class]));else if(s==="style")e.style=gr([e.style,n.style]);else if(el(s)){const r=e[s],o=n[s];o&&r!==o&&!(ze(r)&&r.includes(o))?e[s]=r?[].concat(r,o):o:o==null&&r==null&&!tl(s)&&(e[s]=o)}else s!==""&&(e[s]=n[s])}return e}function Kn(i,e,t,n=null){ai(i,e,7,[t,n])}const d0=gp();let p0=0;function m0(i,e,t){const n=i.type,s=(e?e.appContext:i.appContext)||d0,r={uid:p0++,vnode:i,type:n,parent:e,appContext:s,root:null,next:null,subTree:null,effect:null,update:null,job:null,scope:new z_(!0),render:null,proxy:null,exposed:null,exposeProxy:null,withProxy:null,provides:e?e.provides:Object.create(s.provides),ids:e?e.ids:["",0,0],accessCache:null,renderCache:[],components:null,directives:null,propsOptions:bp(n,s),emitsOptions:vp(n,s),emit:null,emitted:null,propsDefaults:ht,inheritAttrs:n.inheritAttrs,ctx:ht,data:ht,props:ht,attrs:ht,slots:ht,refs:ht,setupState:ht,setupContext:null,suspense:t,suspenseId:t?t.pendingId:0,asyncDep:null,asyncResolved:!1,isMounted:!1,isUnmounted:!1,isDeactivated:!1,bc:null,c:null,bm:null,m:null,bu:null,u:null,um:null,bum:null,da:null,a:null,rtg:null,rtc:null,ec:null,sp:null};return r.ctx={_:r},r.root=e?e.root:r,r.emit=Xg.bind(null,r),i.ce&&i.ce(r),r}let rn=null;const _0=()=>rn||On;let Na,Dc;{const i=rl(),e=(t,n)=>{let s;return(s=i[t])||(s=i[t]=[]),s.push(n),r=>{s.length>1?s.forEach(o=>o(r)):s[0](r)}};Na=e("__VUE_INSTANCE_SETTERS__",t=>rn=t),Dc=e("__VUE_SSR_SETTERS__",t=>xo=t)}const Uo=i=>{const e=rn;return Na(i),i.scope.on(),()=>{i.scope.off(),Na(e)}},Sf=()=>{rn&&rn.scope.off(),Na(null)};function Op(i){return i.vnode.shapeFlag&4}let xo=!1;function g0(i,e=!1,t=!1){e&&Dc(e);const{props:n,children:s}=i.vnode,r=Op(i);Zg(i,n,r,e),t0(i,s,t||e);const o=r?v0(i,e):void 0;return e&&Dc(!1),o}function v0(i,e){const t=i.type;i.accessCache=Object.create(null),i.proxy=new Proxy(i.ctx,Ng);const{setup:n}=t;if(n){Ci();const s=i.setupContext=n.length>1?y0(i):null,r=Uo(i),o=Do(n,i,0,[i.props,s]),a=Od(o);if(Pi(),r(),(a||i.sp)&&!ro(i)&&hp(i),a){if(o.then(Sf,Sf),e)return o.then(l=>{Mf(i,l)}).catch(l=>{ll(l,i,0)});i.asyncDep=o}else Mf(i,o)}else Np(i)}function Mf(i,e,t){We(e)?i.type.__ssrInlineRender?i.ssrRender=e:i.render=e:ct(e)&&(i.setupState=ip(e)),Np(i)}function Np(i,e,t){const n=i.type;i.render||(i.render=n.render||ri);{const s=Uo(i);Ci();try{Fg(i)}finally{Pi(),s()}}}const x0={get(i,e){return qt(i,"get",""),i[e]}};function y0(i){const e=t=>{i.exposed=t||{}};return{attrs:new Proxy(i.attrs,x0),slots:i.slots,emit:i.emit,expose:e}}function dl(i){return i.exposed?i.exposeProxy||(i.exposeProxy=new Proxy(ip(rg(i.exposed)),{get(e,t){if(t in e)return e[t];if(t in oo)return oo[t](i)},has(e,t){return t in e||t in oo}})):i.proxy}function S0(i){return We(i)&&"__vccOpts"in i}const lo=(i,e)=>ug(i,e,xo),M0="3.5.34";/**
* @vue/runtime-dom v3.5.34
* (c) 2018-present Yuxi (Evan) You and Vue contributors
* @license MIT
**/let Uc;const Ef=typeof window<"u"&&window.trustedTypes;if(Ef)try{Uc=Ef.createPolicy("vue",{createHTML:i=>i})}catch{}const Fp=Uc?i=>Uc.createHTML(i):i=>i,E0="http://www.w3.org/2000/svg",b0="http://www.w3.org/1998/Math/MathML",vi=typeof document<"u"?document:null,bf=vi&&vi.createElement("template"),T0={insert:(i,e,t)=>{e.insertBefore(i,t||null)},remove:i=>{const e=i.parentNode;e&&e.removeChild(i)},createElement:(i,e,t,n)=>{const s=e==="svg"?vi.createElementNS(E0,i):e==="mathml"?vi.createElementNS(b0,i):t?vi.createElement(i,{is:t}):vi.createElement(i);return i==="select"&&n&&n.multiple!=null&&s.setAttribute("multiple",n.multiple),s},createText:i=>vi.createTextNode(i),createComment:i=>vi.createComment(i),setText:(i,e)=>{i.nodeValue=e},setElementText:(i,e)=>{i.textContent=e},parentNode:i=>i.parentNode,nextSibling:i=>i.nextSibling,querySelector:i=>vi.querySelector(i),setScopeId(i,e){i.setAttribute(e,"")},insertStaticContent(i,e,t,n,s,r){const o=t?t.previousSibling:e.lastChild;if(s&&(s===r||s.nextSibling))for(;e.insertBefore(s.cloneNode(!0),t),!(s===r||!(s=s.nextSibling)););else{bf.innerHTML=Fp(n==="svg"?`<svg>${i}</svg>`:n==="mathml"?`<math>${i}</math>`:i);const a=bf.content;if(n==="svg"||n==="mathml"){const l=a.firstChild;for(;l.firstChild;)a.appendChild(l.firstChild);a.removeChild(l)}e.insertBefore(a,t)}return[o?o.nextSibling:e.firstChild,t?t.previousSibling:e.lastChild]}},A0=Symbol("_vtc");function w0(i,e,t){const n=i[A0];n&&(e=(e?[e,...n]:[...n]).join(" ")),e==null?i.removeAttribute("class"):t?i.setAttribute("class",e):i.className=e}const Fa=Symbol("_vod"),zp=Symbol("_vsh"),ps={name:"show",beforeMount(i,{value:e},{transition:t}){i[Fa]=i.style.display==="none"?"":i.style.display,t&&e?t.beforeEnter(i):Gr(i,e)},mounted(i,{value:e},{transition:t}){t&&e&&t.enter(i)},updated(i,{value:e,oldValue:t},{transition:n}){!e!=!t&&(n?e?(n.beforeEnter(i),Gr(i,!0),n.enter(i)):n.leave(i,()=>{Gr(i,!1)}):Gr(i,e))},beforeUnmount(i,{value:e}){Gr(i,e)}};function Gr(i,e){i.style.display=e?i[Fa]:"none",i[zp]=!e}const R0=Symbol(""),C0=/(?:^|;)\s*display\s*:/;function P0(i,e,t){const n=i.style,s=bt(t);let r=!1;if(t&&!s){if(e)if(bt(e))for(const o of e.split(";")){const a=o.slice(0,o.indexOf(":")).trim();t[a]==null&&Jr(n,a,"")}else for(const o in e)t[o]==null&&Jr(n,o,"");for(const o in t){o==="display"&&(r=!0);const a=t[o];a!=null?D0(i,o,!bt(e)&&e?e[o]:void 0,a)||Jr(n,o,a):Jr(n,o,"")}}else if(s){if(e!==t){const o=n[R0];o&&(t+=";"+o),n.cssText=t,r=C0.test(t)}}else e&&i.removeAttribute("style");Fa in i&&(i[Fa]=r?n.display:"",i[zp]&&(n.display="none"))}const Tf=/\s*!important$/;function Jr(i,e,t){if(ze(t))t.forEach(n=>Jr(i,e,n));else if(t==null&&(t=""),e.startsWith("--"))i.setProperty(e,t);else{const n=L0(i,e);Tf.test(t)?i.setProperty(Vs(n),t.replace(Tf,""),"important"):i[n]=t}}const Af=["Webkit","Moz","ms"],Ol={};function L0(i,e){const t=Ol[e];if(t)return t;let n=qn(e);if(n!=="filter"&&n in i)return Ol[e]=n;n=zd(n);for(let s=0;s<Af.length;s++){const r=Af[s]+n;if(r in i)return Ol[e]=r}return e}function D0(i,e,t,n){return i.tagName==="TEXTAREA"&&(e==="width"||e==="height")&&bt(n)&&t===n}const wf="http://www.w3.org/1999/xlink";function Rf(i,e,t,n,s,r=O_(e)){n&&e.startsWith("xlink:")?t==null?i.removeAttributeNS(wf,e.slice(6,e.length)):i.setAttributeNS(wf,e,t):t==null||r&&!kd(t)?i.removeAttribute(e):i.setAttribute(e,r?"":oi(t)?String(t):t)}function Cf(i,e,t,n,s){if(e==="innerHTML"||e==="textContent"){t!=null&&(i[e]=e==="innerHTML"?Fp(t):t);return}const r=i.tagName;if(e==="value"&&r!=="PROGRESS"&&!r.includes("-")){const a=r==="OPTION"?i.getAttribute("value")||"":i.value,l=t==null?i.type==="checkbox"?"on":"":String(t);(a!==l||!("_value"in i))&&(i.value=l),t==null&&i.removeAttribute(e),i._value=t;return}let o=!1;if(t===""||t==null){const a=typeof i[e];a==="boolean"?t=kd(t):t==null&&a==="string"?(t="",o=!0):a==="number"&&(t=0,o=!0)}try{i[e]=t}catch{}o&&i.removeAttribute(s||e)}function bs(i,e,t,n){i.addEventListener(e,t,n)}function U0(i,e,t,n){i.removeEventListener(e,t,n)}const Pf=Symbol("_vei");function I0(i,e,t,n,s=null){const r=i[Pf]||(i[Pf]={}),o=r[e];if(n&&o)o.value=n;else{const[a,l]=O0(e);if(n){const c=r[e]=z0(n,s);bs(i,a,c,l)}else o&&(U0(i,a,o,l),r[e]=void 0)}}const Lf=/(?:Once|Passive|Capture)$/;function O0(i){let e;if(Lf.test(i)){e={};let n;for(;n=i.match(Lf);)i=i.slice(0,i.length-n[0].length),e[n[0].toLowerCase()]=!0}return[i[2]===":"?i.slice(3):Vs(i.slice(2)),e]}let Nl=0;const N0=Promise.resolve(),F0=()=>Nl||(N0.then(()=>Nl=0),Nl=Date.now());function z0(i,e){const t=n=>{if(!n._vts)n._vts=Date.now();else if(n._vts<=t.attached)return;ai(B0(n,t.value),e,5,[n])};return t.value=i,t.attached=F0(),t}function B0(i,e){if(ze(e)){const t=i.stopImmediatePropagation;return i.stopImmediatePropagation=()=>{t.call(i),i._stopped=!0},e.map(n=>s=>!s._stopped&&n&&n(s))}else return e}const Df=i=>i.charCodeAt(0)===111&&i.charCodeAt(1)===110&&i.charCodeAt(2)>96&&i.charCodeAt(2)<123,k0=(i,e,t,n,s,r)=>{const o=s==="svg";e==="class"?w0(i,n,o):e==="style"?P0(i,t,n):el(e)?tl(e)||I0(i,e,t,n,r):(e[0]==="."?(e=e.slice(1),!0):e[0]==="^"?(e=e.slice(1),!1):V0(i,e,n,o))?(Cf(i,e,n),!i.tagName.includes("-")&&(e==="value"||e==="checked"||e==="selected")&&Rf(i,e,n,o,r,e!=="value")):i._isVueCE&&(H0(i,e)||i._def.__asyncLoader&&(/[A-Z]/.test(e)||!bt(n)))?Cf(i,qn(e),n,r,e):(e==="true-value"?i._trueValue=n:e==="false-value"&&(i._falseValue=n),Rf(i,e,n,o))};function V0(i,e,t,n){if(n)return!!(e==="innerHTML"||e==="textContent"||e in i&&Df(e)&&We(t));if(e==="spellcheck"||e==="draggable"||e==="translate"||e==="autocorrect"||e==="sandbox"&&i.tagName==="IFRAME"||e==="form"||e==="list"&&i.tagName==="INPUT"||e==="type"&&i.tagName==="TEXTAREA")return!1;if(e==="width"||e==="height"){const s=i.tagName;if(s==="IMG"||s==="VIDEO"||s==="CANVAS"||s==="SOURCE")return!1}return Df(e)&&bt(t)?!1:e in i}function H0(i,e){const t=i._def.props;if(!t)return!1;const n=qn(e);return Array.isArray(t)?t.some(s=>qn(s)===n):Object.keys(t).some(s=>qn(s)===n)}const za=i=>{const e=i.props["onUpdate:modelValue"]||!1;return ze(e)?t=>Ea(e,t):e};function G0(i){i.target.composing=!0}function Uf(i){const e=i.target;e.composing&&(e.composing=!1,e.dispatchEvent(new Event("input")))}const Sr=Symbol("_assign");function If(i,e,t){return e&&(i=i.trim()),t&&(i=sl(i)),i}const ot={created(i,{modifiers:{lazy:e,trim:t,number:n}},s){i[Sr]=za(s);const r=n||s.props&&s.props.type==="number";bs(i,e?"change":"input",o=>{o.target.composing||i[Sr](If(i.value,t,r))}),(t||r)&&bs(i,"change",()=>{i.value=If(i.value,t,r)}),e||(bs(i,"compositionstart",G0),bs(i,"compositionend",Uf),bs(i,"change",Uf))},mounted(i,{value:e}){i.value=e??""},beforeUpdate(i,{value:e,oldValue:t,modifiers:{lazy:n,trim:s,number:r}},o){if(i[Sr]=za(o),i.composing)return;const a=(r||i.type==="number")&&!/^0\d/.test(i.value)?sl(i.value):i.value,l=e??"";if(a===l)return;const c=i.getRootNode();(c instanceof Document||c instanceof ShadowRoot)&&c.activeElement===i&&i.type!=="range"&&(n&&e===t||s&&i.value.trim()===l)||(i.value=l)}},Ic={deep:!0,created(i,{value:e,modifiers:{number:t}},n){const s=nl(e);bs(i,"change",()=>{const r=Array.prototype.filter.call(i.options,o=>o.selected).map(o=>t?sl(Ba(o)):Ba(o));i[Sr](i.multiple?s?new Set(r):r:r[0]),i._assigning=!0,rp(()=>{i._assigning=!1})}),i[Sr]=za(n)},mounted(i,{value:e}){Of(i,e)},beforeUpdate(i,e,t){i[Sr]=za(t)},updated(i,{value:e}){i._assigning||Of(i,e)}};function Of(i,e){const t=i.multiple,n=ze(e);if(!(t&&!n&&!nl(e))){for(let s=0,r=i.options.length;s<r;s++){const o=i.options[s],a=Ba(o);if(t)if(n){const l=typeof a;l==="string"||l==="number"?o.selected=e.some(c=>String(c)===String(a)):o.selected=F_(e,a)>-1}else o.selected=e.has(a);else if(Lo(Ba(o),e)){i.selectedIndex!==s&&(i.selectedIndex=s);return}}!t&&i.selectedIndex!==-1&&(i.selectedIndex=-1)}}function Ba(i){return"_value"in i?i._value:i.value}const W0=Kt({patchProp:k0},T0);let Nf;function X0(){return Nf||(Nf=i0(W0))}const q0=(...i)=>{const e=X0().createApp(...i),{mount:t}=e;return e.mount=n=>{const s=$0(n);if(!s)return;const r=e._component;!We(r)&&!r.render&&!r.template&&(r.template=s.innerHTML),s.nodeType===1&&(s.textContent="");const o=t(s,!1,Y0(s));return s instanceof Element&&(s.removeAttribute("v-cloak"),s.setAttribute("data-v-app","")),o},e};function Y0(i){if(i instanceof SVGElement)return"svg";if(typeof MathMLElement=="function"&&i instanceof MathMLElement)return"mathml"}function $0(i){return bt(i)?document.querySelector(i):i}/**
 * @license
 * Copyright 2010-2023 Three.js Authors
 * SPDX-License-Identifier: MIT
 */const bu="160",Xs={ROTATE:0,DOLLY:1,PAN:2},qs={ROTATE:0,PAN:1,DOLLY_PAN:2,DOLLY_ROTATE:3},j0=0,Ff=1,K0=2,Bp=1,Z0=2,gi=3,ss=0,un=1,Ai=2,Zi=0,Ji=1,ka=2,zf=3,Bf=4,J0=5,Ts=100,Q0=101,ev=102,kf=103,Vf=104,tv=200,nv=201,iv=202,sv=203,Oc=204,Nc=205,rv=206,ov=207,av=208,lv=209,cv=210,uv=211,fv=212,hv=213,dv=214,pv=0,mv=1,_v=2,Va=3,gv=4,vv=5,xv=6,yv=7,kp=0,Sv=1,Mv=2,Qi=0,Ev=1,bv=2,Tv=3,Av=4,wv=5,Rv=6,Vp=300,Rr=301,Cr=302,Fc=303,zc=304,pl=306,Bc=1e3,Wn=1001,kc=1002,tn=1003,Hf=1004,Fl=1005,Dn=1006,Cv=1007,yo=1008,es=1009,Pv=1010,Lv=1011,Tu=1012,Hp=1013,Xi=1014,qi=1015,So=1016,Gp=1017,Wp=1018,Ls=1020,Dv=1021,Xn=1023,Uv=1024,Iv=1025,Ds=1026,Pr=1027,Ov=1028,Xp=1029,Nv=1030,qp=1031,Yp=1033,zl=33776,Bl=33777,kl=33778,Vl=33779,Gf=35840,Wf=35841,Xf=35842,qf=35843,$p=36196,Yf=37492,$f=37496,jf=37808,Kf=37809,Zf=37810,Jf=37811,Qf=37812,eh=37813,th=37814,nh=37815,ih=37816,sh=37817,rh=37818,oh=37819,ah=37820,lh=37821,Hl=36492,ch=36494,uh=36495,Fv=36283,fh=36284,hh=36285,dh=36286,jp=3e3,Us=3001,zv=3200,Bv=3201,kv=0,Vv=1,In="",kt="srgb",Di="srgb-linear",Au="display-p3",ml="display-p3-linear",Ha="linear",mt="srgb",Ga="rec709",Wa="p3",Ys=7680,ph=519,Hv=512,Gv=513,Wv=514,Kp=515,Xv=516,qv=517,Yv=518,$v=519,mh=35044,_h="300 es",Vc=1035,Ri=2e3,Xa=2001;class Hs{addEventListener(e,t){this._listeners===void 0&&(this._listeners={});const n=this._listeners;n[e]===void 0&&(n[e]=[]),n[e].indexOf(t)===-1&&n[e].push(t)}hasEventListener(e,t){if(this._listeners===void 0)return!1;const n=this._listeners;return n[e]!==void 0&&n[e].indexOf(t)!==-1}removeEventListener(e,t){if(this._listeners===void 0)return;const s=this._listeners[e];if(s!==void 0){const r=s.indexOf(t);r!==-1&&s.splice(r,1)}}dispatchEvent(e){if(this._listeners===void 0)return;const n=this._listeners[e.type];if(n!==void 0){e.target=this;const s=n.slice(0);for(let r=0,o=s.length;r<o;r++)s[r].call(this,e);e.target=null}}}const Wt=["00","01","02","03","04","05","06","07","08","09","0a","0b","0c","0d","0e","0f","10","11","12","13","14","15","16","17","18","19","1a","1b","1c","1d","1e","1f","20","21","22","23","24","25","26","27","28","29","2a","2b","2c","2d","2e","2f","30","31","32","33","34","35","36","37","38","39","3a","3b","3c","3d","3e","3f","40","41","42","43","44","45","46","47","48","49","4a","4b","4c","4d","4e","4f","50","51","52","53","54","55","56","57","58","59","5a","5b","5c","5d","5e","5f","60","61","62","63","64","65","66","67","68","69","6a","6b","6c","6d","6e","6f","70","71","72","73","74","75","76","77","78","79","7a","7b","7c","7d","7e","7f","80","81","82","83","84","85","86","87","88","89","8a","8b","8c","8d","8e","8f","90","91","92","93","94","95","96","97","98","99","9a","9b","9c","9d","9e","9f","a0","a1","a2","a3","a4","a5","a6","a7","a8","a9","aa","ab","ac","ad","ae","af","b0","b1","b2","b3","b4","b5","b6","b7","b8","b9","ba","bb","bc","bd","be","bf","c0","c1","c2","c3","c4","c5","c6","c7","c8","c9","ca","cb","cc","cd","ce","cf","d0","d1","d2","d3","d4","d5","d6","d7","d8","d9","da","db","dc","dd","de","df","e0","e1","e2","e3","e4","e5","e6","e7","e8","e9","ea","eb","ec","ed","ee","ef","f0","f1","f2","f3","f4","f5","f6","f7","f8","f9","fa","fb","fc","fd","fe","ff"],Aa=Math.PI/180,Hc=180/Math.PI;function Io(){const i=Math.random()*4294967295|0,e=Math.random()*4294967295|0,t=Math.random()*4294967295|0,n=Math.random()*4294967295|0;return(Wt[i&255]+Wt[i>>8&255]+Wt[i>>16&255]+Wt[i>>24&255]+"-"+Wt[e&255]+Wt[e>>8&255]+"-"+Wt[e>>16&15|64]+Wt[e>>24&255]+"-"+Wt[t&63|128]+Wt[t>>8&255]+"-"+Wt[t>>16&255]+Wt[t>>24&255]+Wt[n&255]+Wt[n>>8&255]+Wt[n>>16&255]+Wt[n>>24&255]).toLowerCase()}function sn(i,e,t){return Math.max(e,Math.min(t,i))}function jv(i,e){return(i%e+e)%e}function Gl(i,e,t){return(1-t)*i+t*e}function gh(i){return(i&i-1)===0&&i!==0}function Gc(i){return Math.pow(2,Math.floor(Math.log(i)/Math.LN2))}function Wr(i,e){switch(e.constructor){case Float32Array:return i;case Uint32Array:return i/4294967295;case Uint16Array:return i/65535;case Uint8Array:return i/255;case Int32Array:return Math.max(i/2147483647,-1);case Int16Array:return Math.max(i/32767,-1);case Int8Array:return Math.max(i/127,-1);default:throw new Error("Invalid component type.")}}function on(i,e){switch(e.constructor){case Float32Array:return i;case Uint32Array:return Math.round(i*4294967295);case Uint16Array:return Math.round(i*65535);case Uint8Array:return Math.round(i*255);case Int32Array:return Math.round(i*2147483647);case Int16Array:return Math.round(i*32767);case Int8Array:return Math.round(i*127);default:throw new Error("Invalid component type.")}}const Kv={DEG2RAD:Aa};class He{constructor(e=0,t=0){He.prototype.isVector2=!0,this.x=e,this.y=t}get width(){return this.x}set width(e){this.x=e}get height(){return this.y}set height(e){this.y=e}set(e,t){return this.x=e,this.y=t,this}setScalar(e){return this.x=e,this.y=e,this}setX(e){return this.x=e,this}setY(e){return this.y=e,this}setComponent(e,t){switch(e){case 0:this.x=t;break;case 1:this.y=t;break;default:throw new Error("index is out of range: "+e)}return this}getComponent(e){switch(e){case 0:return this.x;case 1:return this.y;default:throw new Error("index is out of range: "+e)}}clone(){return new this.constructor(this.x,this.y)}copy(e){return this.x=e.x,this.y=e.y,this}add(e){return this.x+=e.x,this.y+=e.y,this}addScalar(e){return this.x+=e,this.y+=e,this}addVectors(e,t){return this.x=e.x+t.x,this.y=e.y+t.y,this}addScaledVector(e,t){return this.x+=e.x*t,this.y+=e.y*t,this}sub(e){return this.x-=e.x,this.y-=e.y,this}subScalar(e){return this.x-=e,this.y-=e,this}subVectors(e,t){return this.x=e.x-t.x,this.y=e.y-t.y,this}multiply(e){return this.x*=e.x,this.y*=e.y,this}multiplyScalar(e){return this.x*=e,this.y*=e,this}divide(e){return this.x/=e.x,this.y/=e.y,this}divideScalar(e){return this.multiplyScalar(1/e)}applyMatrix3(e){const t=this.x,n=this.y,s=e.elements;return this.x=s[0]*t+s[3]*n+s[6],this.y=s[1]*t+s[4]*n+s[7],this}min(e){return this.x=Math.min(this.x,e.x),this.y=Math.min(this.y,e.y),this}max(e){return this.x=Math.max(this.x,e.x),this.y=Math.max(this.y,e.y),this}clamp(e,t){return this.x=Math.max(e.x,Math.min(t.x,this.x)),this.y=Math.max(e.y,Math.min(t.y,this.y)),this}clampScalar(e,t){return this.x=Math.max(e,Math.min(t,this.x)),this.y=Math.max(e,Math.min(t,this.y)),this}clampLength(e,t){const n=this.length();return this.divideScalar(n||1).multiplyScalar(Math.max(e,Math.min(t,n)))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this}negate(){return this.x=-this.x,this.y=-this.y,this}dot(e){return this.x*e.x+this.y*e.y}cross(e){return this.x*e.y-this.y*e.x}lengthSq(){return this.x*this.x+this.y*this.y}length(){return Math.sqrt(this.x*this.x+this.y*this.y)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)}normalize(){return this.divideScalar(this.length()||1)}angle(){return Math.atan2(-this.y,-this.x)+Math.PI}angleTo(e){const t=Math.sqrt(this.lengthSq()*e.lengthSq());if(t===0)return Math.PI/2;const n=this.dot(e)/t;return Math.acos(sn(n,-1,1))}distanceTo(e){return Math.sqrt(this.distanceToSquared(e))}distanceToSquared(e){const t=this.x-e.x,n=this.y-e.y;return t*t+n*n}manhattanDistanceTo(e){return Math.abs(this.x-e.x)+Math.abs(this.y-e.y)}setLength(e){return this.normalize().multiplyScalar(e)}lerp(e,t){return this.x+=(e.x-this.x)*t,this.y+=(e.y-this.y)*t,this}lerpVectors(e,t,n){return this.x=e.x+(t.x-e.x)*n,this.y=e.y+(t.y-e.y)*n,this}equals(e){return e.x===this.x&&e.y===this.y}fromArray(e,t=0){return this.x=e[t],this.y=e[t+1],this}toArray(e=[],t=0){return e[t]=this.x,e[t+1]=this.y,e}fromBufferAttribute(e,t){return this.x=e.getX(t),this.y=e.getY(t),this}rotateAround(e,t){const n=Math.cos(t),s=Math.sin(t),r=this.x-e.x,o=this.y-e.y;return this.x=r*n-o*s+e.x,this.y=r*s+o*n+e.y,this}random(){return this.x=Math.random(),this.y=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y}}class je{constructor(e,t,n,s,r,o,a,l,c){je.prototype.isMatrix3=!0,this.elements=[1,0,0,0,1,0,0,0,1],e!==void 0&&this.set(e,t,n,s,r,o,a,l,c)}set(e,t,n,s,r,o,a,l,c){const u=this.elements;return u[0]=e,u[1]=s,u[2]=a,u[3]=t,u[4]=r,u[5]=l,u[6]=n,u[7]=o,u[8]=c,this}identity(){return this.set(1,0,0,0,1,0,0,0,1),this}copy(e){const t=this.elements,n=e.elements;return t[0]=n[0],t[1]=n[1],t[2]=n[2],t[3]=n[3],t[4]=n[4],t[5]=n[5],t[6]=n[6],t[7]=n[7],t[8]=n[8],this}extractBasis(e,t,n){return e.setFromMatrix3Column(this,0),t.setFromMatrix3Column(this,1),n.setFromMatrix3Column(this,2),this}setFromMatrix4(e){const t=e.elements;return this.set(t[0],t[4],t[8],t[1],t[5],t[9],t[2],t[6],t[10]),this}multiply(e){return this.multiplyMatrices(this,e)}premultiply(e){return this.multiplyMatrices(e,this)}multiplyMatrices(e,t){const n=e.elements,s=t.elements,r=this.elements,o=n[0],a=n[3],l=n[6],c=n[1],u=n[4],f=n[7],h=n[2],d=n[5],g=n[8],_=s[0],m=s[3],p=s[6],x=s[1],y=s[4],S=s[7],R=s[2],L=s[5],w=s[8];return r[0]=o*_+a*x+l*R,r[3]=o*m+a*y+l*L,r[6]=o*p+a*S+l*w,r[1]=c*_+u*x+f*R,r[4]=c*m+u*y+f*L,r[7]=c*p+u*S+f*w,r[2]=h*_+d*x+g*R,r[5]=h*m+d*y+g*L,r[8]=h*p+d*S+g*w,this}multiplyScalar(e){const t=this.elements;return t[0]*=e,t[3]*=e,t[6]*=e,t[1]*=e,t[4]*=e,t[7]*=e,t[2]*=e,t[5]*=e,t[8]*=e,this}determinant(){const e=this.elements,t=e[0],n=e[1],s=e[2],r=e[3],o=e[4],a=e[5],l=e[6],c=e[7],u=e[8];return t*o*u-t*a*c-n*r*u+n*a*l+s*r*c-s*o*l}invert(){const e=this.elements,t=e[0],n=e[1],s=e[2],r=e[3],o=e[4],a=e[5],l=e[6],c=e[7],u=e[8],f=u*o-a*c,h=a*l-u*r,d=c*r-o*l,g=t*f+n*h+s*d;if(g===0)return this.set(0,0,0,0,0,0,0,0,0);const _=1/g;return e[0]=f*_,e[1]=(s*c-u*n)*_,e[2]=(a*n-s*o)*_,e[3]=h*_,e[4]=(u*t-s*l)*_,e[5]=(s*r-a*t)*_,e[6]=d*_,e[7]=(n*l-c*t)*_,e[8]=(o*t-n*r)*_,this}transpose(){let e;const t=this.elements;return e=t[1],t[1]=t[3],t[3]=e,e=t[2],t[2]=t[6],t[6]=e,e=t[5],t[5]=t[7],t[7]=e,this}getNormalMatrix(e){return this.setFromMatrix4(e).invert().transpose()}transposeIntoArray(e){const t=this.elements;return e[0]=t[0],e[1]=t[3],e[2]=t[6],e[3]=t[1],e[4]=t[4],e[5]=t[7],e[6]=t[2],e[7]=t[5],e[8]=t[8],this}setUvTransform(e,t,n,s,r,o,a){const l=Math.cos(r),c=Math.sin(r);return this.set(n*l,n*c,-n*(l*o+c*a)+o+e,-s*c,s*l,-s*(-c*o+l*a)+a+t,0,0,1),this}scale(e,t){return this.premultiply(Wl.makeScale(e,t)),this}rotate(e){return this.premultiply(Wl.makeRotation(-e)),this}translate(e,t){return this.premultiply(Wl.makeTranslation(e,t)),this}makeTranslation(e,t){return e.isVector2?this.set(1,0,e.x,0,1,e.y,0,0,1):this.set(1,0,e,0,1,t,0,0,1),this}makeRotation(e){const t=Math.cos(e),n=Math.sin(e);return this.set(t,-n,0,n,t,0,0,0,1),this}makeScale(e,t){return this.set(e,0,0,0,t,0,0,0,1),this}equals(e){const t=this.elements,n=e.elements;for(let s=0;s<9;s++)if(t[s]!==n[s])return!1;return!0}fromArray(e,t=0){for(let n=0;n<9;n++)this.elements[n]=e[n+t];return this}toArray(e=[],t=0){const n=this.elements;return e[t]=n[0],e[t+1]=n[1],e[t+2]=n[2],e[t+3]=n[3],e[t+4]=n[4],e[t+5]=n[5],e[t+6]=n[6],e[t+7]=n[7],e[t+8]=n[8],e}clone(){return new this.constructor().fromArray(this.elements)}}const Wl=new je;function Zp(i){for(let e=i.length-1;e>=0;--e)if(i[e]>=65535)return!0;return!1}function qa(i){return document.createElementNS("http://www.w3.org/1999/xhtml",i)}function Zv(){const i=qa("canvas");return i.style.display="block",i}const vh={};function co(i){i in vh||(vh[i]=!0,console.warn(i))}const xh=new je().set(.8224621,.177538,0,.0331941,.9668058,0,.0170827,.0723974,.9105199),yh=new je().set(1.2249401,-.2249404,0,-.0420569,1.0420571,0,-.0196376,-.0786361,1.0982735),qo={[Di]:{transfer:Ha,primaries:Ga,toReference:i=>i,fromReference:i=>i},[kt]:{transfer:mt,primaries:Ga,toReference:i=>i.convertSRGBToLinear(),fromReference:i=>i.convertLinearToSRGB()},[ml]:{transfer:Ha,primaries:Wa,toReference:i=>i.applyMatrix3(yh),fromReference:i=>i.applyMatrix3(xh)},[Au]:{transfer:mt,primaries:Wa,toReference:i=>i.convertSRGBToLinear().applyMatrix3(yh),fromReference:i=>i.applyMatrix3(xh).convertLinearToSRGB()}},Jv=new Set([Di,ml]),at={enabled:!0,_workingColorSpace:Di,get workingColorSpace(){return this._workingColorSpace},set workingColorSpace(i){if(!Jv.has(i))throw new Error(`Unsupported working color space, "${i}".`);this._workingColorSpace=i},convert:function(i,e,t){if(this.enabled===!1||e===t||!e||!t)return i;const n=qo[e].toReference,s=qo[t].fromReference;return s(n(i))},fromWorkingColorSpace:function(i,e){return this.convert(i,this._workingColorSpace,e)},toWorkingColorSpace:function(i,e){return this.convert(i,e,this._workingColorSpace)},getPrimaries:function(i){return qo[i].primaries},getTransfer:function(i){return i===In?Ha:qo[i].transfer}};function Mr(i){return i<.04045?i*.0773993808:Math.pow(i*.9478672986+.0521327014,2.4)}function Xl(i){return i<.0031308?i*12.92:1.055*Math.pow(i,.41666)-.055}let $s;class Jp{static getDataURL(e){if(/^data:/i.test(e.src)||typeof HTMLCanvasElement>"u")return e.src;let t;if(e instanceof HTMLCanvasElement)t=e;else{$s===void 0&&($s=qa("canvas")),$s.width=e.width,$s.height=e.height;const n=$s.getContext("2d");e instanceof ImageData?n.putImageData(e,0,0):n.drawImage(e,0,0,e.width,e.height),t=$s}return t.width>2048||t.height>2048?(console.warn("THREE.ImageUtils.getDataURL: Image converted to jpg for performance reasons",e),t.toDataURL("image/jpeg",.6)):t.toDataURL("image/png")}static sRGBToLinear(e){if(typeof HTMLImageElement<"u"&&e instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&e instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&e instanceof ImageBitmap){const t=qa("canvas");t.width=e.width,t.height=e.height;const n=t.getContext("2d");n.drawImage(e,0,0,e.width,e.height);const s=n.getImageData(0,0,e.width,e.height),r=s.data;for(let o=0;o<r.length;o++)r[o]=Mr(r[o]/255)*255;return n.putImageData(s,0,0),t}else if(e.data){const t=e.data.slice(0);for(let n=0;n<t.length;n++)t instanceof Uint8Array||t instanceof Uint8ClampedArray?t[n]=Math.floor(Mr(t[n]/255)*255):t[n]=Mr(t[n]);return{data:t,width:e.width,height:e.height}}else return console.warn("THREE.ImageUtils.sRGBToLinear(): Unsupported image type. No color space conversion applied."),e}}let Qv=0;class Qp{constructor(e=null){this.isSource=!0,Object.defineProperty(this,"id",{value:Qv++}),this.uuid=Io(),this.data=e,this.version=0}set needsUpdate(e){e===!0&&this.version++}toJSON(e){const t=e===void 0||typeof e=="string";if(!t&&e.images[this.uuid]!==void 0)return e.images[this.uuid];const n={uuid:this.uuid,url:""},s=this.data;if(s!==null){let r;if(Array.isArray(s)){r=[];for(let o=0,a=s.length;o<a;o++)s[o].isDataTexture?r.push(ql(s[o].image)):r.push(ql(s[o]))}else r=ql(s);n.url=r}return t||(e.images[this.uuid]=n),n}}function ql(i){return typeof HTMLImageElement<"u"&&i instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&i instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&i instanceof ImageBitmap?Jp.getDataURL(i):i.data?{data:Array.from(i.data),width:i.width,height:i.height,type:i.data.constructor.name}:(console.warn("THREE.Texture: Unable to serialize Texture."),{})}let ex=0;class Tn extends Hs{constructor(e=Tn.DEFAULT_IMAGE,t=Tn.DEFAULT_MAPPING,n=Wn,s=Wn,r=Dn,o=yo,a=Xn,l=es,c=Tn.DEFAULT_ANISOTROPY,u=In){super(),this.isTexture=!0,Object.defineProperty(this,"id",{value:ex++}),this.uuid=Io(),this.name="",this.source=new Qp(e),this.mipmaps=[],this.mapping=t,this.channel=0,this.wrapS=n,this.wrapT=s,this.magFilter=r,this.minFilter=o,this.anisotropy=c,this.format=a,this.internalFormat=null,this.type=l,this.offset=new He(0,0),this.repeat=new He(1,1),this.center=new He(0,0),this.rotation=0,this.matrixAutoUpdate=!0,this.matrix=new je,this.generateMipmaps=!0,this.premultiplyAlpha=!1,this.flipY=!0,this.unpackAlignment=4,typeof u=="string"?this.colorSpace=u:(co("THREE.Texture: Property .encoding has been replaced by .colorSpace."),this.colorSpace=u===Us?kt:In),this.userData={},this.version=0,this.onUpdate=null,this.isRenderTargetTexture=!1,this.needsPMREMUpdate=!1}get image(){return this.source.data}set image(e=null){this.source.data=e}updateMatrix(){this.matrix.setUvTransform(this.offset.x,this.offset.y,this.repeat.x,this.repeat.y,this.rotation,this.center.x,this.center.y)}clone(){return new this.constructor().copy(this)}copy(e){return this.name=e.name,this.source=e.source,this.mipmaps=e.mipmaps.slice(0),this.mapping=e.mapping,this.channel=e.channel,this.wrapS=e.wrapS,this.wrapT=e.wrapT,this.magFilter=e.magFilter,this.minFilter=e.minFilter,this.anisotropy=e.anisotropy,this.format=e.format,this.internalFormat=e.internalFormat,this.type=e.type,this.offset.copy(e.offset),this.repeat.copy(e.repeat),this.center.copy(e.center),this.rotation=e.rotation,this.matrixAutoUpdate=e.matrixAutoUpdate,this.matrix.copy(e.matrix),this.generateMipmaps=e.generateMipmaps,this.premultiplyAlpha=e.premultiplyAlpha,this.flipY=e.flipY,this.unpackAlignment=e.unpackAlignment,this.colorSpace=e.colorSpace,this.userData=JSON.parse(JSON.stringify(e.userData)),this.needsUpdate=!0,this}toJSON(e){const t=e===void 0||typeof e=="string";if(!t&&e.textures[this.uuid]!==void 0)return e.textures[this.uuid];const n={metadata:{version:4.6,type:"Texture",generator:"Texture.toJSON"},uuid:this.uuid,name:this.name,image:this.source.toJSON(e).uuid,mapping:this.mapping,channel:this.channel,repeat:[this.repeat.x,this.repeat.y],offset:[this.offset.x,this.offset.y],center:[this.center.x,this.center.y],rotation:this.rotation,wrap:[this.wrapS,this.wrapT],format:this.format,internalFormat:this.internalFormat,type:this.type,colorSpace:this.colorSpace,minFilter:this.minFilter,magFilter:this.magFilter,anisotropy:this.anisotropy,flipY:this.flipY,generateMipmaps:this.generateMipmaps,premultiplyAlpha:this.premultiplyAlpha,unpackAlignment:this.unpackAlignment};return Object.keys(this.userData).length>0&&(n.userData=this.userData),t||(e.textures[this.uuid]=n),n}dispose(){this.dispatchEvent({type:"dispose"})}transformUv(e){if(this.mapping!==Vp)return e;if(e.applyMatrix3(this.matrix),e.x<0||e.x>1)switch(this.wrapS){case Bc:e.x=e.x-Math.floor(e.x);break;case Wn:e.x=e.x<0?0:1;break;case kc:Math.abs(Math.floor(e.x)%2)===1?e.x=Math.ceil(e.x)-e.x:e.x=e.x-Math.floor(e.x);break}if(e.y<0||e.y>1)switch(this.wrapT){case Bc:e.y=e.y-Math.floor(e.y);break;case Wn:e.y=e.y<0?0:1;break;case kc:Math.abs(Math.floor(e.y)%2)===1?e.y=Math.ceil(e.y)-e.y:e.y=e.y-Math.floor(e.y);break}return this.flipY&&(e.y=1-e.y),e}set needsUpdate(e){e===!0&&(this.version++,this.source.needsUpdate=!0)}get encoding(){return co("THREE.Texture: Property .encoding has been replaced by .colorSpace."),this.colorSpace===kt?Us:jp}set encoding(e){co("THREE.Texture: Property .encoding has been replaced by .colorSpace."),this.colorSpace=e===Us?kt:In}}Tn.DEFAULT_IMAGE=null;Tn.DEFAULT_MAPPING=Vp;Tn.DEFAULT_ANISOTROPY=1;class Ft{constructor(e=0,t=0,n=0,s=1){Ft.prototype.isVector4=!0,this.x=e,this.y=t,this.z=n,this.w=s}get width(){return this.z}set width(e){this.z=e}get height(){return this.w}set height(e){this.w=e}set(e,t,n,s){return this.x=e,this.y=t,this.z=n,this.w=s,this}setScalar(e){return this.x=e,this.y=e,this.z=e,this.w=e,this}setX(e){return this.x=e,this}setY(e){return this.y=e,this}setZ(e){return this.z=e,this}setW(e){return this.w=e,this}setComponent(e,t){switch(e){case 0:this.x=t;break;case 1:this.y=t;break;case 2:this.z=t;break;case 3:this.w=t;break;default:throw new Error("index is out of range: "+e)}return this}getComponent(e){switch(e){case 0:return this.x;case 1:return this.y;case 2:return this.z;case 3:return this.w;default:throw new Error("index is out of range: "+e)}}clone(){return new this.constructor(this.x,this.y,this.z,this.w)}copy(e){return this.x=e.x,this.y=e.y,this.z=e.z,this.w=e.w!==void 0?e.w:1,this}add(e){return this.x+=e.x,this.y+=e.y,this.z+=e.z,this.w+=e.w,this}addScalar(e){return this.x+=e,this.y+=e,this.z+=e,this.w+=e,this}addVectors(e,t){return this.x=e.x+t.x,this.y=e.y+t.y,this.z=e.z+t.z,this.w=e.w+t.w,this}addScaledVector(e,t){return this.x+=e.x*t,this.y+=e.y*t,this.z+=e.z*t,this.w+=e.w*t,this}sub(e){return this.x-=e.x,this.y-=e.y,this.z-=e.z,this.w-=e.w,this}subScalar(e){return this.x-=e,this.y-=e,this.z-=e,this.w-=e,this}subVectors(e,t){return this.x=e.x-t.x,this.y=e.y-t.y,this.z=e.z-t.z,this.w=e.w-t.w,this}multiply(e){return this.x*=e.x,this.y*=e.y,this.z*=e.z,this.w*=e.w,this}multiplyScalar(e){return this.x*=e,this.y*=e,this.z*=e,this.w*=e,this}applyMatrix4(e){const t=this.x,n=this.y,s=this.z,r=this.w,o=e.elements;return this.x=o[0]*t+o[4]*n+o[8]*s+o[12]*r,this.y=o[1]*t+o[5]*n+o[9]*s+o[13]*r,this.z=o[2]*t+o[6]*n+o[10]*s+o[14]*r,this.w=o[3]*t+o[7]*n+o[11]*s+o[15]*r,this}divideScalar(e){return this.multiplyScalar(1/e)}setAxisAngleFromQuaternion(e){this.w=2*Math.acos(e.w);const t=Math.sqrt(1-e.w*e.w);return t<1e-4?(this.x=1,this.y=0,this.z=0):(this.x=e.x/t,this.y=e.y/t,this.z=e.z/t),this}setAxisAngleFromRotationMatrix(e){let t,n,s,r;const l=e.elements,c=l[0],u=l[4],f=l[8],h=l[1],d=l[5],g=l[9],_=l[2],m=l[6],p=l[10];if(Math.abs(u-h)<.01&&Math.abs(f-_)<.01&&Math.abs(g-m)<.01){if(Math.abs(u+h)<.1&&Math.abs(f+_)<.1&&Math.abs(g+m)<.1&&Math.abs(c+d+p-3)<.1)return this.set(1,0,0,0),this;t=Math.PI;const y=(c+1)/2,S=(d+1)/2,R=(p+1)/2,L=(u+h)/4,w=(f+_)/4,B=(g+m)/4;return y>S&&y>R?y<.01?(n=0,s=.707106781,r=.707106781):(n=Math.sqrt(y),s=L/n,r=w/n):S>R?S<.01?(n=.707106781,s=0,r=.707106781):(s=Math.sqrt(S),n=L/s,r=B/s):R<.01?(n=.707106781,s=.707106781,r=0):(r=Math.sqrt(R),n=w/r,s=B/r),this.set(n,s,r,t),this}let x=Math.sqrt((m-g)*(m-g)+(f-_)*(f-_)+(h-u)*(h-u));return Math.abs(x)<.001&&(x=1),this.x=(m-g)/x,this.y=(f-_)/x,this.z=(h-u)/x,this.w=Math.acos((c+d+p-1)/2),this}min(e){return this.x=Math.min(this.x,e.x),this.y=Math.min(this.y,e.y),this.z=Math.min(this.z,e.z),this.w=Math.min(this.w,e.w),this}max(e){return this.x=Math.max(this.x,e.x),this.y=Math.max(this.y,e.y),this.z=Math.max(this.z,e.z),this.w=Math.max(this.w,e.w),this}clamp(e,t){return this.x=Math.max(e.x,Math.min(t.x,this.x)),this.y=Math.max(e.y,Math.min(t.y,this.y)),this.z=Math.max(e.z,Math.min(t.z,this.z)),this.w=Math.max(e.w,Math.min(t.w,this.w)),this}clampScalar(e,t){return this.x=Math.max(e,Math.min(t,this.x)),this.y=Math.max(e,Math.min(t,this.y)),this.z=Math.max(e,Math.min(t,this.z)),this.w=Math.max(e,Math.min(t,this.w)),this}clampLength(e,t){const n=this.length();return this.divideScalar(n||1).multiplyScalar(Math.max(e,Math.min(t,n)))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this.w=Math.floor(this.w),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this.w=Math.ceil(this.w),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this.w=Math.round(this.w),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this.w=Math.trunc(this.w),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this.w=-this.w,this}dot(e){return this.x*e.x+this.y*e.y+this.z*e.z+this.w*e.w}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)+Math.abs(this.w)}normalize(){return this.divideScalar(this.length()||1)}setLength(e){return this.normalize().multiplyScalar(e)}lerp(e,t){return this.x+=(e.x-this.x)*t,this.y+=(e.y-this.y)*t,this.z+=(e.z-this.z)*t,this.w+=(e.w-this.w)*t,this}lerpVectors(e,t,n){return this.x=e.x+(t.x-e.x)*n,this.y=e.y+(t.y-e.y)*n,this.z=e.z+(t.z-e.z)*n,this.w=e.w+(t.w-e.w)*n,this}equals(e){return e.x===this.x&&e.y===this.y&&e.z===this.z&&e.w===this.w}fromArray(e,t=0){return this.x=e[t],this.y=e[t+1],this.z=e[t+2],this.w=e[t+3],this}toArray(e=[],t=0){return e[t]=this.x,e[t+1]=this.y,e[t+2]=this.z,e[t+3]=this.w,e}fromBufferAttribute(e,t){return this.x=e.getX(t),this.y=e.getY(t),this.z=e.getZ(t),this.w=e.getW(t),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this.w=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z,yield this.w}}class tx extends Hs{constructor(e=1,t=1,n={}){super(),this.isRenderTarget=!0,this.width=e,this.height=t,this.depth=1,this.scissor=new Ft(0,0,e,t),this.scissorTest=!1,this.viewport=new Ft(0,0,e,t);const s={width:e,height:t,depth:1};n.encoding!==void 0&&(co("THREE.WebGLRenderTarget: option.encoding has been replaced by option.colorSpace."),n.colorSpace=n.encoding===Us?kt:In),n=Object.assign({generateMipmaps:!1,internalFormat:null,minFilter:Dn,depthBuffer:!0,stencilBuffer:!1,depthTexture:null,samples:0},n),this.texture=new Tn(s,n.mapping,n.wrapS,n.wrapT,n.magFilter,n.minFilter,n.format,n.type,n.anisotropy,n.colorSpace),this.texture.isRenderTargetTexture=!0,this.texture.flipY=!1,this.texture.generateMipmaps=n.generateMipmaps,this.texture.internalFormat=n.internalFormat,this.depthBuffer=n.depthBuffer,this.stencilBuffer=n.stencilBuffer,this.depthTexture=n.depthTexture,this.samples=n.samples}setSize(e,t,n=1){(this.width!==e||this.height!==t||this.depth!==n)&&(this.width=e,this.height=t,this.depth=n,this.texture.image.width=e,this.texture.image.height=t,this.texture.image.depth=n,this.dispose()),this.viewport.set(0,0,e,t),this.scissor.set(0,0,e,t)}clone(){return new this.constructor().copy(this)}copy(e){this.width=e.width,this.height=e.height,this.depth=e.depth,this.scissor.copy(e.scissor),this.scissorTest=e.scissorTest,this.viewport.copy(e.viewport),this.texture=e.texture.clone(),this.texture.isRenderTargetTexture=!0;const t=Object.assign({},e.texture.image);return this.texture.source=new Qp(t),this.depthBuffer=e.depthBuffer,this.stencilBuffer=e.stencilBuffer,e.depthTexture!==null&&(this.depthTexture=e.depthTexture.clone()),this.samples=e.samples,this}dispose(){this.dispatchEvent({type:"dispose"})}}class Bs extends tx{constructor(e=1,t=1,n={}){super(e,t,n),this.isWebGLRenderTarget=!0}}class em extends Tn{constructor(e=null,t=1,n=1,s=1){super(null),this.isDataArrayTexture=!0,this.image={data:e,width:t,height:n,depth:s},this.magFilter=tn,this.minFilter=tn,this.wrapR=Wn,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}}class nx extends Tn{constructor(e=null,t=1,n=1,s=1){super(null),this.isData3DTexture=!0,this.image={data:e,width:t,height:n,depth:s},this.magFilter=tn,this.minFilter=tn,this.wrapR=Wn,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}}class ks{constructor(e=0,t=0,n=0,s=1){this.isQuaternion=!0,this._x=e,this._y=t,this._z=n,this._w=s}static slerpFlat(e,t,n,s,r,o,a){let l=n[s+0],c=n[s+1],u=n[s+2],f=n[s+3];const h=r[o+0],d=r[o+1],g=r[o+2],_=r[o+3];if(a===0){e[t+0]=l,e[t+1]=c,e[t+2]=u,e[t+3]=f;return}if(a===1){e[t+0]=h,e[t+1]=d,e[t+2]=g,e[t+3]=_;return}if(f!==_||l!==h||c!==d||u!==g){let m=1-a;const p=l*h+c*d+u*g+f*_,x=p>=0?1:-1,y=1-p*p;if(y>Number.EPSILON){const R=Math.sqrt(y),L=Math.atan2(R,p*x);m=Math.sin(m*L)/R,a=Math.sin(a*L)/R}const S=a*x;if(l=l*m+h*S,c=c*m+d*S,u=u*m+g*S,f=f*m+_*S,m===1-a){const R=1/Math.sqrt(l*l+c*c+u*u+f*f);l*=R,c*=R,u*=R,f*=R}}e[t]=l,e[t+1]=c,e[t+2]=u,e[t+3]=f}static multiplyQuaternionsFlat(e,t,n,s,r,o){const a=n[s],l=n[s+1],c=n[s+2],u=n[s+3],f=r[o],h=r[o+1],d=r[o+2],g=r[o+3];return e[t]=a*g+u*f+l*d-c*h,e[t+1]=l*g+u*h+c*f-a*d,e[t+2]=c*g+u*d+a*h-l*f,e[t+3]=u*g-a*f-l*h-c*d,e}get x(){return this._x}set x(e){this._x=e,this._onChangeCallback()}get y(){return this._y}set y(e){this._y=e,this._onChangeCallback()}get z(){return this._z}set z(e){this._z=e,this._onChangeCallback()}get w(){return this._w}set w(e){this._w=e,this._onChangeCallback()}set(e,t,n,s){return this._x=e,this._y=t,this._z=n,this._w=s,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._w)}copy(e){return this._x=e.x,this._y=e.y,this._z=e.z,this._w=e.w,this._onChangeCallback(),this}setFromEuler(e,t=!0){const n=e._x,s=e._y,r=e._z,o=e._order,a=Math.cos,l=Math.sin,c=a(n/2),u=a(s/2),f=a(r/2),h=l(n/2),d=l(s/2),g=l(r/2);switch(o){case"XYZ":this._x=h*u*f+c*d*g,this._y=c*d*f-h*u*g,this._z=c*u*g+h*d*f,this._w=c*u*f-h*d*g;break;case"YXZ":this._x=h*u*f+c*d*g,this._y=c*d*f-h*u*g,this._z=c*u*g-h*d*f,this._w=c*u*f+h*d*g;break;case"ZXY":this._x=h*u*f-c*d*g,this._y=c*d*f+h*u*g,this._z=c*u*g+h*d*f,this._w=c*u*f-h*d*g;break;case"ZYX":this._x=h*u*f-c*d*g,this._y=c*d*f+h*u*g,this._z=c*u*g-h*d*f,this._w=c*u*f+h*d*g;break;case"YZX":this._x=h*u*f+c*d*g,this._y=c*d*f+h*u*g,this._z=c*u*g-h*d*f,this._w=c*u*f-h*d*g;break;case"XZY":this._x=h*u*f-c*d*g,this._y=c*d*f-h*u*g,this._z=c*u*g+h*d*f,this._w=c*u*f+h*d*g;break;default:console.warn("THREE.Quaternion: .setFromEuler() encountered an unknown order: "+o)}return t===!0&&this._onChangeCallback(),this}setFromAxisAngle(e,t){const n=t/2,s=Math.sin(n);return this._x=e.x*s,this._y=e.y*s,this._z=e.z*s,this._w=Math.cos(n),this._onChangeCallback(),this}setFromRotationMatrix(e){const t=e.elements,n=t[0],s=t[4],r=t[8],o=t[1],a=t[5],l=t[9],c=t[2],u=t[6],f=t[10],h=n+a+f;if(h>0){const d=.5/Math.sqrt(h+1);this._w=.25/d,this._x=(u-l)*d,this._y=(r-c)*d,this._z=(o-s)*d}else if(n>a&&n>f){const d=2*Math.sqrt(1+n-a-f);this._w=(u-l)/d,this._x=.25*d,this._y=(s+o)/d,this._z=(r+c)/d}else if(a>f){const d=2*Math.sqrt(1+a-n-f);this._w=(r-c)/d,this._x=(s+o)/d,this._y=.25*d,this._z=(l+u)/d}else{const d=2*Math.sqrt(1+f-n-a);this._w=(o-s)/d,this._x=(r+c)/d,this._y=(l+u)/d,this._z=.25*d}return this._onChangeCallback(),this}setFromUnitVectors(e,t){let n=e.dot(t)+1;return n<Number.EPSILON?(n=0,Math.abs(e.x)>Math.abs(e.z)?(this._x=-e.y,this._y=e.x,this._z=0,this._w=n):(this._x=0,this._y=-e.z,this._z=e.y,this._w=n)):(this._x=e.y*t.z-e.z*t.y,this._y=e.z*t.x-e.x*t.z,this._z=e.x*t.y-e.y*t.x,this._w=n),this.normalize()}angleTo(e){return 2*Math.acos(Math.abs(sn(this.dot(e),-1,1)))}rotateTowards(e,t){const n=this.angleTo(e);if(n===0)return this;const s=Math.min(1,t/n);return this.slerp(e,s),this}identity(){return this.set(0,0,0,1)}invert(){return this.conjugate()}conjugate(){return this._x*=-1,this._y*=-1,this._z*=-1,this._onChangeCallback(),this}dot(e){return this._x*e._x+this._y*e._y+this._z*e._z+this._w*e._w}lengthSq(){return this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w}length(){return Math.sqrt(this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w)}normalize(){let e=this.length();return e===0?(this._x=0,this._y=0,this._z=0,this._w=1):(e=1/e,this._x=this._x*e,this._y=this._y*e,this._z=this._z*e,this._w=this._w*e),this._onChangeCallback(),this}multiply(e){return this.multiplyQuaternions(this,e)}premultiply(e){return this.multiplyQuaternions(e,this)}multiplyQuaternions(e,t){const n=e._x,s=e._y,r=e._z,o=e._w,a=t._x,l=t._y,c=t._z,u=t._w;return this._x=n*u+o*a+s*c-r*l,this._y=s*u+o*l+r*a-n*c,this._z=r*u+o*c+n*l-s*a,this._w=o*u-n*a-s*l-r*c,this._onChangeCallback(),this}slerp(e,t){if(t===0)return this;if(t===1)return this.copy(e);const n=this._x,s=this._y,r=this._z,o=this._w;let a=o*e._w+n*e._x+s*e._y+r*e._z;if(a<0?(this._w=-e._w,this._x=-e._x,this._y=-e._y,this._z=-e._z,a=-a):this.copy(e),a>=1)return this._w=o,this._x=n,this._y=s,this._z=r,this;const l=1-a*a;if(l<=Number.EPSILON){const d=1-t;return this._w=d*o+t*this._w,this._x=d*n+t*this._x,this._y=d*s+t*this._y,this._z=d*r+t*this._z,this.normalize(),this}const c=Math.sqrt(l),u=Math.atan2(c,a),f=Math.sin((1-t)*u)/c,h=Math.sin(t*u)/c;return this._w=o*f+this._w*h,this._x=n*f+this._x*h,this._y=s*f+this._y*h,this._z=r*f+this._z*h,this._onChangeCallback(),this}slerpQuaternions(e,t,n){return this.copy(e).slerp(t,n)}random(){const e=Math.random(),t=Math.sqrt(1-e),n=Math.sqrt(e),s=2*Math.PI*Math.random(),r=2*Math.PI*Math.random();return this.set(t*Math.cos(s),n*Math.sin(r),n*Math.cos(r),t*Math.sin(s))}equals(e){return e._x===this._x&&e._y===this._y&&e._z===this._z&&e._w===this._w}fromArray(e,t=0){return this._x=e[t],this._y=e[t+1],this._z=e[t+2],this._w=e[t+3],this._onChangeCallback(),this}toArray(e=[],t=0){return e[t]=this._x,e[t+1]=this._y,e[t+2]=this._z,e[t+3]=this._w,e}fromBufferAttribute(e,t){return this._x=e.getX(t),this._y=e.getY(t),this._z=e.getZ(t),this._w=e.getW(t),this._onChangeCallback(),this}toJSON(){return this.toArray()}_onChange(e){return this._onChangeCallback=e,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._w}}class ${constructor(e=0,t=0,n=0){$.prototype.isVector3=!0,this.x=e,this.y=t,this.z=n}set(e,t,n){return n===void 0&&(n=this.z),this.x=e,this.y=t,this.z=n,this}setScalar(e){return this.x=e,this.y=e,this.z=e,this}setX(e){return this.x=e,this}setY(e){return this.y=e,this}setZ(e){return this.z=e,this}setComponent(e,t){switch(e){case 0:this.x=t;break;case 1:this.y=t;break;case 2:this.z=t;break;default:throw new Error("index is out of range: "+e)}return this}getComponent(e){switch(e){case 0:return this.x;case 1:return this.y;case 2:return this.z;default:throw new Error("index is out of range: "+e)}}clone(){return new this.constructor(this.x,this.y,this.z)}copy(e){return this.x=e.x,this.y=e.y,this.z=e.z,this}add(e){return this.x+=e.x,this.y+=e.y,this.z+=e.z,this}addScalar(e){return this.x+=e,this.y+=e,this.z+=e,this}addVectors(e,t){return this.x=e.x+t.x,this.y=e.y+t.y,this.z=e.z+t.z,this}addScaledVector(e,t){return this.x+=e.x*t,this.y+=e.y*t,this.z+=e.z*t,this}sub(e){return this.x-=e.x,this.y-=e.y,this.z-=e.z,this}subScalar(e){return this.x-=e,this.y-=e,this.z-=e,this}subVectors(e,t){return this.x=e.x-t.x,this.y=e.y-t.y,this.z=e.z-t.z,this}multiply(e){return this.x*=e.x,this.y*=e.y,this.z*=e.z,this}multiplyScalar(e){return this.x*=e,this.y*=e,this.z*=e,this}multiplyVectors(e,t){return this.x=e.x*t.x,this.y=e.y*t.y,this.z=e.z*t.z,this}applyEuler(e){return this.applyQuaternion(Sh.setFromEuler(e))}applyAxisAngle(e,t){return this.applyQuaternion(Sh.setFromAxisAngle(e,t))}applyMatrix3(e){const t=this.x,n=this.y,s=this.z,r=e.elements;return this.x=r[0]*t+r[3]*n+r[6]*s,this.y=r[1]*t+r[4]*n+r[7]*s,this.z=r[2]*t+r[5]*n+r[8]*s,this}applyNormalMatrix(e){return this.applyMatrix3(e).normalize()}applyMatrix4(e){const t=this.x,n=this.y,s=this.z,r=e.elements,o=1/(r[3]*t+r[7]*n+r[11]*s+r[15]);return this.x=(r[0]*t+r[4]*n+r[8]*s+r[12])*o,this.y=(r[1]*t+r[5]*n+r[9]*s+r[13])*o,this.z=(r[2]*t+r[6]*n+r[10]*s+r[14])*o,this}applyQuaternion(e){const t=this.x,n=this.y,s=this.z,r=e.x,o=e.y,a=e.z,l=e.w,c=2*(o*s-a*n),u=2*(a*t-r*s),f=2*(r*n-o*t);return this.x=t+l*c+o*f-a*u,this.y=n+l*u+a*c-r*f,this.z=s+l*f+r*u-o*c,this}project(e){return this.applyMatrix4(e.matrixWorldInverse).applyMatrix4(e.projectionMatrix)}unproject(e){return this.applyMatrix4(e.projectionMatrixInverse).applyMatrix4(e.matrixWorld)}transformDirection(e){const t=this.x,n=this.y,s=this.z,r=e.elements;return this.x=r[0]*t+r[4]*n+r[8]*s,this.y=r[1]*t+r[5]*n+r[9]*s,this.z=r[2]*t+r[6]*n+r[10]*s,this.normalize()}divide(e){return this.x/=e.x,this.y/=e.y,this.z/=e.z,this}divideScalar(e){return this.multiplyScalar(1/e)}min(e){return this.x=Math.min(this.x,e.x),this.y=Math.min(this.y,e.y),this.z=Math.min(this.z,e.z),this}max(e){return this.x=Math.max(this.x,e.x),this.y=Math.max(this.y,e.y),this.z=Math.max(this.z,e.z),this}clamp(e,t){return this.x=Math.max(e.x,Math.min(t.x,this.x)),this.y=Math.max(e.y,Math.min(t.y,this.y)),this.z=Math.max(e.z,Math.min(t.z,this.z)),this}clampScalar(e,t){return this.x=Math.max(e,Math.min(t,this.x)),this.y=Math.max(e,Math.min(t,this.y)),this.z=Math.max(e,Math.min(t,this.z)),this}clampLength(e,t){const n=this.length();return this.divideScalar(n||1).multiplyScalar(Math.max(e,Math.min(t,n)))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this}dot(e){return this.x*e.x+this.y*e.y+this.z*e.z}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)}normalize(){return this.divideScalar(this.length()||1)}setLength(e){return this.normalize().multiplyScalar(e)}lerp(e,t){return this.x+=(e.x-this.x)*t,this.y+=(e.y-this.y)*t,this.z+=(e.z-this.z)*t,this}lerpVectors(e,t,n){return this.x=e.x+(t.x-e.x)*n,this.y=e.y+(t.y-e.y)*n,this.z=e.z+(t.z-e.z)*n,this}cross(e){return this.crossVectors(this,e)}crossVectors(e,t){const n=e.x,s=e.y,r=e.z,o=t.x,a=t.y,l=t.z;return this.x=s*l-r*a,this.y=r*o-n*l,this.z=n*a-s*o,this}projectOnVector(e){const t=e.lengthSq();if(t===0)return this.set(0,0,0);const n=e.dot(this)/t;return this.copy(e).multiplyScalar(n)}projectOnPlane(e){return Yl.copy(this).projectOnVector(e),this.sub(Yl)}reflect(e){return this.sub(Yl.copy(e).multiplyScalar(2*this.dot(e)))}angleTo(e){const t=Math.sqrt(this.lengthSq()*e.lengthSq());if(t===0)return Math.PI/2;const n=this.dot(e)/t;return Math.acos(sn(n,-1,1))}distanceTo(e){return Math.sqrt(this.distanceToSquared(e))}distanceToSquared(e){const t=this.x-e.x,n=this.y-e.y,s=this.z-e.z;return t*t+n*n+s*s}manhattanDistanceTo(e){return Math.abs(this.x-e.x)+Math.abs(this.y-e.y)+Math.abs(this.z-e.z)}setFromSpherical(e){return this.setFromSphericalCoords(e.radius,e.phi,e.theta)}setFromSphericalCoords(e,t,n){const s=Math.sin(t)*e;return this.x=s*Math.sin(n),this.y=Math.cos(t)*e,this.z=s*Math.cos(n),this}setFromCylindrical(e){return this.setFromCylindricalCoords(e.radius,e.theta,e.y)}setFromCylindricalCoords(e,t,n){return this.x=e*Math.sin(t),this.y=n,this.z=e*Math.cos(t),this}setFromMatrixPosition(e){const t=e.elements;return this.x=t[12],this.y=t[13],this.z=t[14],this}setFromMatrixScale(e){const t=this.setFromMatrixColumn(e,0).length(),n=this.setFromMatrixColumn(e,1).length(),s=this.setFromMatrixColumn(e,2).length();return this.x=t,this.y=n,this.z=s,this}setFromMatrixColumn(e,t){return this.fromArray(e.elements,t*4)}setFromMatrix3Column(e,t){return this.fromArray(e.elements,t*3)}setFromEuler(e){return this.x=e._x,this.y=e._y,this.z=e._z,this}setFromColor(e){return this.x=e.r,this.y=e.g,this.z=e.b,this}equals(e){return e.x===this.x&&e.y===this.y&&e.z===this.z}fromArray(e,t=0){return this.x=e[t],this.y=e[t+1],this.z=e[t+2],this}toArray(e=[],t=0){return e[t]=this.x,e[t+1]=this.y,e[t+2]=this.z,e}fromBufferAttribute(e,t){return this.x=e.getX(t),this.y=e.getY(t),this.z=e.getZ(t),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this}randomDirection(){const e=(Math.random()-.5)*2,t=Math.random()*Math.PI*2,n=Math.sqrt(1-e**2);return this.x=n*Math.cos(t),this.y=n*Math.sin(t),this.z=e,this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z}}const Yl=new $,Sh=new ks;class Oo{constructor(e=new $(1/0,1/0,1/0),t=new $(-1/0,-1/0,-1/0)){this.isBox3=!0,this.min=e,this.max=t}set(e,t){return this.min.copy(e),this.max.copy(t),this}setFromArray(e){this.makeEmpty();for(let t=0,n=e.length;t<n;t+=3)this.expandByPoint(kn.fromArray(e,t));return this}setFromBufferAttribute(e){this.makeEmpty();for(let t=0,n=e.count;t<n;t++)this.expandByPoint(kn.fromBufferAttribute(e,t));return this}setFromPoints(e){this.makeEmpty();for(let t=0,n=e.length;t<n;t++)this.expandByPoint(e[t]);return this}setFromCenterAndSize(e,t){const n=kn.copy(t).multiplyScalar(.5);return this.min.copy(e).sub(n),this.max.copy(e).add(n),this}setFromObject(e,t=!1){return this.makeEmpty(),this.expandByObject(e,t)}clone(){return new this.constructor().copy(this)}copy(e){return this.min.copy(e.min),this.max.copy(e.max),this}makeEmpty(){return this.min.x=this.min.y=this.min.z=1/0,this.max.x=this.max.y=this.max.z=-1/0,this}isEmpty(){return this.max.x<this.min.x||this.max.y<this.min.y||this.max.z<this.min.z}getCenter(e){return this.isEmpty()?e.set(0,0,0):e.addVectors(this.min,this.max).multiplyScalar(.5)}getSize(e){return this.isEmpty()?e.set(0,0,0):e.subVectors(this.max,this.min)}expandByPoint(e){return this.min.min(e),this.max.max(e),this}expandByVector(e){return this.min.sub(e),this.max.add(e),this}expandByScalar(e){return this.min.addScalar(-e),this.max.addScalar(e),this}expandByObject(e,t=!1){e.updateWorldMatrix(!1,!1);const n=e.geometry;if(n!==void 0){const r=n.getAttribute("position");if(t===!0&&r!==void 0&&e.isInstancedMesh!==!0)for(let o=0,a=r.count;o<a;o++)e.isMesh===!0?e.getVertexPosition(o,kn):kn.fromBufferAttribute(r,o),kn.applyMatrix4(e.matrixWorld),this.expandByPoint(kn);else e.boundingBox!==void 0?(e.boundingBox===null&&e.computeBoundingBox(),Yo.copy(e.boundingBox)):(n.boundingBox===null&&n.computeBoundingBox(),Yo.copy(n.boundingBox)),Yo.applyMatrix4(e.matrixWorld),this.union(Yo)}const s=e.children;for(let r=0,o=s.length;r<o;r++)this.expandByObject(s[r],t);return this}containsPoint(e){return!(e.x<this.min.x||e.x>this.max.x||e.y<this.min.y||e.y>this.max.y||e.z<this.min.z||e.z>this.max.z)}containsBox(e){return this.min.x<=e.min.x&&e.max.x<=this.max.x&&this.min.y<=e.min.y&&e.max.y<=this.max.y&&this.min.z<=e.min.z&&e.max.z<=this.max.z}getParameter(e,t){return t.set((e.x-this.min.x)/(this.max.x-this.min.x),(e.y-this.min.y)/(this.max.y-this.min.y),(e.z-this.min.z)/(this.max.z-this.min.z))}intersectsBox(e){return!(e.max.x<this.min.x||e.min.x>this.max.x||e.max.y<this.min.y||e.min.y>this.max.y||e.max.z<this.min.z||e.min.z>this.max.z)}intersectsSphere(e){return this.clampPoint(e.center,kn),kn.distanceToSquared(e.center)<=e.radius*e.radius}intersectsPlane(e){let t,n;return e.normal.x>0?(t=e.normal.x*this.min.x,n=e.normal.x*this.max.x):(t=e.normal.x*this.max.x,n=e.normal.x*this.min.x),e.normal.y>0?(t+=e.normal.y*this.min.y,n+=e.normal.y*this.max.y):(t+=e.normal.y*this.max.y,n+=e.normal.y*this.min.y),e.normal.z>0?(t+=e.normal.z*this.min.z,n+=e.normal.z*this.max.z):(t+=e.normal.z*this.max.z,n+=e.normal.z*this.min.z),t<=-e.constant&&n>=-e.constant}intersectsTriangle(e){if(this.isEmpty())return!1;this.getCenter(Xr),$o.subVectors(this.max,Xr),js.subVectors(e.a,Xr),Ks.subVectors(e.b,Xr),Zs.subVectors(e.c,Xr),Fi.subVectors(Ks,js),zi.subVectors(Zs,Ks),ms.subVectors(js,Zs);let t=[0,-Fi.z,Fi.y,0,-zi.z,zi.y,0,-ms.z,ms.y,Fi.z,0,-Fi.x,zi.z,0,-zi.x,ms.z,0,-ms.x,-Fi.y,Fi.x,0,-zi.y,zi.x,0,-ms.y,ms.x,0];return!$l(t,js,Ks,Zs,$o)||(t=[1,0,0,0,1,0,0,0,1],!$l(t,js,Ks,Zs,$o))?!1:(jo.crossVectors(Fi,zi),t=[jo.x,jo.y,jo.z],$l(t,js,Ks,Zs,$o))}clampPoint(e,t){return t.copy(e).clamp(this.min,this.max)}distanceToPoint(e){return this.clampPoint(e,kn).distanceTo(e)}getBoundingSphere(e){return this.isEmpty()?e.makeEmpty():(this.getCenter(e.center),e.radius=this.getSize(kn).length()*.5),e}intersect(e){return this.min.max(e.min),this.max.min(e.max),this.isEmpty()&&this.makeEmpty(),this}union(e){return this.min.min(e.min),this.max.max(e.max),this}applyMatrix4(e){return this.isEmpty()?this:(fi[0].set(this.min.x,this.min.y,this.min.z).applyMatrix4(e),fi[1].set(this.min.x,this.min.y,this.max.z).applyMatrix4(e),fi[2].set(this.min.x,this.max.y,this.min.z).applyMatrix4(e),fi[3].set(this.min.x,this.max.y,this.max.z).applyMatrix4(e),fi[4].set(this.max.x,this.min.y,this.min.z).applyMatrix4(e),fi[5].set(this.max.x,this.min.y,this.max.z).applyMatrix4(e),fi[6].set(this.max.x,this.max.y,this.min.z).applyMatrix4(e),fi[7].set(this.max.x,this.max.y,this.max.z).applyMatrix4(e),this.setFromPoints(fi),this)}translate(e){return this.min.add(e),this.max.add(e),this}equals(e){return e.min.equals(this.min)&&e.max.equals(this.max)}}const fi=[new $,new $,new $,new $,new $,new $,new $,new $],kn=new $,Yo=new Oo,js=new $,Ks=new $,Zs=new $,Fi=new $,zi=new $,ms=new $,Xr=new $,$o=new $,jo=new $,_s=new $;function $l(i,e,t,n,s){for(let r=0,o=i.length-3;r<=o;r+=3){_s.fromArray(i,r);const a=s.x*Math.abs(_s.x)+s.y*Math.abs(_s.y)+s.z*Math.abs(_s.z),l=e.dot(_s),c=t.dot(_s),u=n.dot(_s);if(Math.max(-Math.max(l,c,u),Math.min(l,c,u))>a)return!1}return!0}const ix=new Oo,qr=new $,jl=new $;class _l{constructor(e=new $,t=-1){this.isSphere=!0,this.center=e,this.radius=t}set(e,t){return this.center.copy(e),this.radius=t,this}setFromPoints(e,t){const n=this.center;t!==void 0?n.copy(t):ix.setFromPoints(e).getCenter(n);let s=0;for(let r=0,o=e.length;r<o;r++)s=Math.max(s,n.distanceToSquared(e[r]));return this.radius=Math.sqrt(s),this}copy(e){return this.center.copy(e.center),this.radius=e.radius,this}isEmpty(){return this.radius<0}makeEmpty(){return this.center.set(0,0,0),this.radius=-1,this}containsPoint(e){return e.distanceToSquared(this.center)<=this.radius*this.radius}distanceToPoint(e){return e.distanceTo(this.center)-this.radius}intersectsSphere(e){const t=this.radius+e.radius;return e.center.distanceToSquared(this.center)<=t*t}intersectsBox(e){return e.intersectsSphere(this)}intersectsPlane(e){return Math.abs(e.distanceToPoint(this.center))<=this.radius}clampPoint(e,t){const n=this.center.distanceToSquared(e);return t.copy(e),n>this.radius*this.radius&&(t.sub(this.center).normalize(),t.multiplyScalar(this.radius).add(this.center)),t}getBoundingBox(e){return this.isEmpty()?(e.makeEmpty(),e):(e.set(this.center,this.center),e.expandByScalar(this.radius),e)}applyMatrix4(e){return this.center.applyMatrix4(e),this.radius=this.radius*e.getMaxScaleOnAxis(),this}translate(e){return this.center.add(e),this}expandByPoint(e){if(this.isEmpty())return this.center.copy(e),this.radius=0,this;qr.subVectors(e,this.center);const t=qr.lengthSq();if(t>this.radius*this.radius){const n=Math.sqrt(t),s=(n-this.radius)*.5;this.center.addScaledVector(qr,s/n),this.radius+=s}return this}union(e){return e.isEmpty()?this:this.isEmpty()?(this.copy(e),this):(this.center.equals(e.center)===!0?this.radius=Math.max(this.radius,e.radius):(jl.subVectors(e.center,this.center).setLength(e.radius),this.expandByPoint(qr.copy(e.center).add(jl)),this.expandByPoint(qr.copy(e.center).sub(jl))),this)}equals(e){return e.center.equals(this.center)&&e.radius===this.radius}clone(){return new this.constructor().copy(this)}}const hi=new $,Kl=new $,Ko=new $,Bi=new $,Zl=new $,Zo=new $,Jl=new $;class gl{constructor(e=new $,t=new $(0,0,-1)){this.origin=e,this.direction=t}set(e,t){return this.origin.copy(e),this.direction.copy(t),this}copy(e){return this.origin.copy(e.origin),this.direction.copy(e.direction),this}at(e,t){return t.copy(this.origin).addScaledVector(this.direction,e)}lookAt(e){return this.direction.copy(e).sub(this.origin).normalize(),this}recast(e){return this.origin.copy(this.at(e,hi)),this}closestPointToPoint(e,t){t.subVectors(e,this.origin);const n=t.dot(this.direction);return n<0?t.copy(this.origin):t.copy(this.origin).addScaledVector(this.direction,n)}distanceToPoint(e){return Math.sqrt(this.distanceSqToPoint(e))}distanceSqToPoint(e){const t=hi.subVectors(e,this.origin).dot(this.direction);return t<0?this.origin.distanceToSquared(e):(hi.copy(this.origin).addScaledVector(this.direction,t),hi.distanceToSquared(e))}distanceSqToSegment(e,t,n,s){Kl.copy(e).add(t).multiplyScalar(.5),Ko.copy(t).sub(e).normalize(),Bi.copy(this.origin).sub(Kl);const r=e.distanceTo(t)*.5,o=-this.direction.dot(Ko),a=Bi.dot(this.direction),l=-Bi.dot(Ko),c=Bi.lengthSq(),u=Math.abs(1-o*o);let f,h,d,g;if(u>0)if(f=o*l-a,h=o*a-l,g=r*u,f>=0)if(h>=-g)if(h<=g){const _=1/u;f*=_,h*=_,d=f*(f+o*h+2*a)+h*(o*f+h+2*l)+c}else h=r,f=Math.max(0,-(o*h+a)),d=-f*f+h*(h+2*l)+c;else h=-r,f=Math.max(0,-(o*h+a)),d=-f*f+h*(h+2*l)+c;else h<=-g?(f=Math.max(0,-(-o*r+a)),h=f>0?-r:Math.min(Math.max(-r,-l),r),d=-f*f+h*(h+2*l)+c):h<=g?(f=0,h=Math.min(Math.max(-r,-l),r),d=h*(h+2*l)+c):(f=Math.max(0,-(o*r+a)),h=f>0?r:Math.min(Math.max(-r,-l),r),d=-f*f+h*(h+2*l)+c);else h=o>0?-r:r,f=Math.max(0,-(o*h+a)),d=-f*f+h*(h+2*l)+c;return n&&n.copy(this.origin).addScaledVector(this.direction,f),s&&s.copy(Kl).addScaledVector(Ko,h),d}intersectSphere(e,t){hi.subVectors(e.center,this.origin);const n=hi.dot(this.direction),s=hi.dot(hi)-n*n,r=e.radius*e.radius;if(s>r)return null;const o=Math.sqrt(r-s),a=n-o,l=n+o;return l<0?null:a<0?this.at(l,t):this.at(a,t)}intersectsSphere(e){return this.distanceSqToPoint(e.center)<=e.radius*e.radius}distanceToPlane(e){const t=e.normal.dot(this.direction);if(t===0)return e.distanceToPoint(this.origin)===0?0:null;const n=-(this.origin.dot(e.normal)+e.constant)/t;return n>=0?n:null}intersectPlane(e,t){const n=this.distanceToPlane(e);return n===null?null:this.at(n,t)}intersectsPlane(e){const t=e.distanceToPoint(this.origin);return t===0||e.normal.dot(this.direction)*t<0}intersectBox(e,t){let n,s,r,o,a,l;const c=1/this.direction.x,u=1/this.direction.y,f=1/this.direction.z,h=this.origin;return c>=0?(n=(e.min.x-h.x)*c,s=(e.max.x-h.x)*c):(n=(e.max.x-h.x)*c,s=(e.min.x-h.x)*c),u>=0?(r=(e.min.y-h.y)*u,o=(e.max.y-h.y)*u):(r=(e.max.y-h.y)*u,o=(e.min.y-h.y)*u),n>o||r>s||((r>n||isNaN(n))&&(n=r),(o<s||isNaN(s))&&(s=o),f>=0?(a=(e.min.z-h.z)*f,l=(e.max.z-h.z)*f):(a=(e.max.z-h.z)*f,l=(e.min.z-h.z)*f),n>l||a>s)||((a>n||n!==n)&&(n=a),(l<s||s!==s)&&(s=l),s<0)?null:this.at(n>=0?n:s,t)}intersectsBox(e){return this.intersectBox(e,hi)!==null}intersectTriangle(e,t,n,s,r){Zl.subVectors(t,e),Zo.subVectors(n,e),Jl.crossVectors(Zl,Zo);let o=this.direction.dot(Jl),a;if(o>0){if(s)return null;a=1}else if(o<0)a=-1,o=-o;else return null;Bi.subVectors(this.origin,e);const l=a*this.direction.dot(Zo.crossVectors(Bi,Zo));if(l<0)return null;const c=a*this.direction.dot(Zl.cross(Bi));if(c<0||l+c>o)return null;const u=-a*Bi.dot(Jl);return u<0?null:this.at(u/o,r)}applyMatrix4(e){return this.origin.applyMatrix4(e),this.direction.transformDirection(e),this}equals(e){return e.origin.equals(this.origin)&&e.direction.equals(this.direction)}clone(){return new this.constructor().copy(this)}}class Lt{constructor(e,t,n,s,r,o,a,l,c,u,f,h,d,g,_,m){Lt.prototype.isMatrix4=!0,this.elements=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],e!==void 0&&this.set(e,t,n,s,r,o,a,l,c,u,f,h,d,g,_,m)}set(e,t,n,s,r,o,a,l,c,u,f,h,d,g,_,m){const p=this.elements;return p[0]=e,p[4]=t,p[8]=n,p[12]=s,p[1]=r,p[5]=o,p[9]=a,p[13]=l,p[2]=c,p[6]=u,p[10]=f,p[14]=h,p[3]=d,p[7]=g,p[11]=_,p[15]=m,this}identity(){return this.set(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1),this}clone(){return new Lt().fromArray(this.elements)}copy(e){const t=this.elements,n=e.elements;return t[0]=n[0],t[1]=n[1],t[2]=n[2],t[3]=n[3],t[4]=n[4],t[5]=n[5],t[6]=n[6],t[7]=n[7],t[8]=n[8],t[9]=n[9],t[10]=n[10],t[11]=n[11],t[12]=n[12],t[13]=n[13],t[14]=n[14],t[15]=n[15],this}copyPosition(e){const t=this.elements,n=e.elements;return t[12]=n[12],t[13]=n[13],t[14]=n[14],this}setFromMatrix3(e){const t=e.elements;return this.set(t[0],t[3],t[6],0,t[1],t[4],t[7],0,t[2],t[5],t[8],0,0,0,0,1),this}extractBasis(e,t,n){return e.setFromMatrixColumn(this,0),t.setFromMatrixColumn(this,1),n.setFromMatrixColumn(this,2),this}makeBasis(e,t,n){return this.set(e.x,t.x,n.x,0,e.y,t.y,n.y,0,e.z,t.z,n.z,0,0,0,0,1),this}extractRotation(e){const t=this.elements,n=e.elements,s=1/Js.setFromMatrixColumn(e,0).length(),r=1/Js.setFromMatrixColumn(e,1).length(),o=1/Js.setFromMatrixColumn(e,2).length();return t[0]=n[0]*s,t[1]=n[1]*s,t[2]=n[2]*s,t[3]=0,t[4]=n[4]*r,t[5]=n[5]*r,t[6]=n[6]*r,t[7]=0,t[8]=n[8]*o,t[9]=n[9]*o,t[10]=n[10]*o,t[11]=0,t[12]=0,t[13]=0,t[14]=0,t[15]=1,this}makeRotationFromEuler(e){const t=this.elements,n=e.x,s=e.y,r=e.z,o=Math.cos(n),a=Math.sin(n),l=Math.cos(s),c=Math.sin(s),u=Math.cos(r),f=Math.sin(r);if(e.order==="XYZ"){const h=o*u,d=o*f,g=a*u,_=a*f;t[0]=l*u,t[4]=-l*f,t[8]=c,t[1]=d+g*c,t[5]=h-_*c,t[9]=-a*l,t[2]=_-h*c,t[6]=g+d*c,t[10]=o*l}else if(e.order==="YXZ"){const h=l*u,d=l*f,g=c*u,_=c*f;t[0]=h+_*a,t[4]=g*a-d,t[8]=o*c,t[1]=o*f,t[5]=o*u,t[9]=-a,t[2]=d*a-g,t[6]=_+h*a,t[10]=o*l}else if(e.order==="ZXY"){const h=l*u,d=l*f,g=c*u,_=c*f;t[0]=h-_*a,t[4]=-o*f,t[8]=g+d*a,t[1]=d+g*a,t[5]=o*u,t[9]=_-h*a,t[2]=-o*c,t[6]=a,t[10]=o*l}else if(e.order==="ZYX"){const h=o*u,d=o*f,g=a*u,_=a*f;t[0]=l*u,t[4]=g*c-d,t[8]=h*c+_,t[1]=l*f,t[5]=_*c+h,t[9]=d*c-g,t[2]=-c,t[6]=a*l,t[10]=o*l}else if(e.order==="YZX"){const h=o*l,d=o*c,g=a*l,_=a*c;t[0]=l*u,t[4]=_-h*f,t[8]=g*f+d,t[1]=f,t[5]=o*u,t[9]=-a*u,t[2]=-c*u,t[6]=d*f+g,t[10]=h-_*f}else if(e.order==="XZY"){const h=o*l,d=o*c,g=a*l,_=a*c;t[0]=l*u,t[4]=-f,t[8]=c*u,t[1]=h*f+_,t[5]=o*u,t[9]=d*f-g,t[2]=g*f-d,t[6]=a*u,t[10]=_*f+h}return t[3]=0,t[7]=0,t[11]=0,t[12]=0,t[13]=0,t[14]=0,t[15]=1,this}makeRotationFromQuaternion(e){return this.compose(sx,e,rx)}lookAt(e,t,n){const s=this.elements;return gn.subVectors(e,t),gn.lengthSq()===0&&(gn.z=1),gn.normalize(),ki.crossVectors(n,gn),ki.lengthSq()===0&&(Math.abs(n.z)===1?gn.x+=1e-4:gn.z+=1e-4,gn.normalize(),ki.crossVectors(n,gn)),ki.normalize(),Jo.crossVectors(gn,ki),s[0]=ki.x,s[4]=Jo.x,s[8]=gn.x,s[1]=ki.y,s[5]=Jo.y,s[9]=gn.y,s[2]=ki.z,s[6]=Jo.z,s[10]=gn.z,this}multiply(e){return this.multiplyMatrices(this,e)}premultiply(e){return this.multiplyMatrices(e,this)}multiplyMatrices(e,t){const n=e.elements,s=t.elements,r=this.elements,o=n[0],a=n[4],l=n[8],c=n[12],u=n[1],f=n[5],h=n[9],d=n[13],g=n[2],_=n[6],m=n[10],p=n[14],x=n[3],y=n[7],S=n[11],R=n[15],L=s[0],w=s[4],B=s[8],v=s[12],b=s[1],N=s[5],A=s[9],I=s[13],O=s[2],k=s[6],H=s[10],q=s[14],Z=s[3],W=s[7],j=s[11],G=s[15];return r[0]=o*L+a*b+l*O+c*Z,r[4]=o*w+a*N+l*k+c*W,r[8]=o*B+a*A+l*H+c*j,r[12]=o*v+a*I+l*q+c*G,r[1]=u*L+f*b+h*O+d*Z,r[5]=u*w+f*N+h*k+d*W,r[9]=u*B+f*A+h*H+d*j,r[13]=u*v+f*I+h*q+d*G,r[2]=g*L+_*b+m*O+p*Z,r[6]=g*w+_*N+m*k+p*W,r[10]=g*B+_*A+m*H+p*j,r[14]=g*v+_*I+m*q+p*G,r[3]=x*L+y*b+S*O+R*Z,r[7]=x*w+y*N+S*k+R*W,r[11]=x*B+y*A+S*H+R*j,r[15]=x*v+y*I+S*q+R*G,this}multiplyScalar(e){const t=this.elements;return t[0]*=e,t[4]*=e,t[8]*=e,t[12]*=e,t[1]*=e,t[5]*=e,t[9]*=e,t[13]*=e,t[2]*=e,t[6]*=e,t[10]*=e,t[14]*=e,t[3]*=e,t[7]*=e,t[11]*=e,t[15]*=e,this}determinant(){const e=this.elements,t=e[0],n=e[4],s=e[8],r=e[12],o=e[1],a=e[5],l=e[9],c=e[13],u=e[2],f=e[6],h=e[10],d=e[14],g=e[3],_=e[7],m=e[11],p=e[15];return g*(+r*l*f-s*c*f-r*a*h+n*c*h+s*a*d-n*l*d)+_*(+t*l*d-t*c*h+r*o*h-s*o*d+s*c*u-r*l*u)+m*(+t*c*f-t*a*d-r*o*f+n*o*d+r*a*u-n*c*u)+p*(-s*a*u-t*l*f+t*a*h+s*o*f-n*o*h+n*l*u)}transpose(){const e=this.elements;let t;return t=e[1],e[1]=e[4],e[4]=t,t=e[2],e[2]=e[8],e[8]=t,t=e[6],e[6]=e[9],e[9]=t,t=e[3],e[3]=e[12],e[12]=t,t=e[7],e[7]=e[13],e[13]=t,t=e[11],e[11]=e[14],e[14]=t,this}setPosition(e,t,n){const s=this.elements;return e.isVector3?(s[12]=e.x,s[13]=e.y,s[14]=e.z):(s[12]=e,s[13]=t,s[14]=n),this}invert(){const e=this.elements,t=e[0],n=e[1],s=e[2],r=e[3],o=e[4],a=e[5],l=e[6],c=e[7],u=e[8],f=e[9],h=e[10],d=e[11],g=e[12],_=e[13],m=e[14],p=e[15],x=f*m*c-_*h*c+_*l*d-a*m*d-f*l*p+a*h*p,y=g*h*c-u*m*c-g*l*d+o*m*d+u*l*p-o*h*p,S=u*_*c-g*f*c+g*a*d-o*_*d-u*a*p+o*f*p,R=g*f*l-u*_*l-g*a*h+o*_*h+u*a*m-o*f*m,L=t*x+n*y+s*S+r*R;if(L===0)return this.set(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0);const w=1/L;return e[0]=x*w,e[1]=(_*h*r-f*m*r-_*s*d+n*m*d+f*s*p-n*h*p)*w,e[2]=(a*m*r-_*l*r+_*s*c-n*m*c-a*s*p+n*l*p)*w,e[3]=(f*l*r-a*h*r-f*s*c+n*h*c+a*s*d-n*l*d)*w,e[4]=y*w,e[5]=(u*m*r-g*h*r+g*s*d-t*m*d-u*s*p+t*h*p)*w,e[6]=(g*l*r-o*m*r-g*s*c+t*m*c+o*s*p-t*l*p)*w,e[7]=(o*h*r-u*l*r+u*s*c-t*h*c-o*s*d+t*l*d)*w,e[8]=S*w,e[9]=(g*f*r-u*_*r-g*n*d+t*_*d+u*n*p-t*f*p)*w,e[10]=(o*_*r-g*a*r+g*n*c-t*_*c-o*n*p+t*a*p)*w,e[11]=(u*a*r-o*f*r-u*n*c+t*f*c+o*n*d-t*a*d)*w,e[12]=R*w,e[13]=(u*_*s-g*f*s+g*n*h-t*_*h-u*n*m+t*f*m)*w,e[14]=(g*a*s-o*_*s-g*n*l+t*_*l+o*n*m-t*a*m)*w,e[15]=(o*f*s-u*a*s+u*n*l-t*f*l-o*n*h+t*a*h)*w,this}scale(e){const t=this.elements,n=e.x,s=e.y,r=e.z;return t[0]*=n,t[4]*=s,t[8]*=r,t[1]*=n,t[5]*=s,t[9]*=r,t[2]*=n,t[6]*=s,t[10]*=r,t[3]*=n,t[7]*=s,t[11]*=r,this}getMaxScaleOnAxis(){const e=this.elements,t=e[0]*e[0]+e[1]*e[1]+e[2]*e[2],n=e[4]*e[4]+e[5]*e[5]+e[6]*e[6],s=e[8]*e[8]+e[9]*e[9]+e[10]*e[10];return Math.sqrt(Math.max(t,n,s))}makeTranslation(e,t,n){return e.isVector3?this.set(1,0,0,e.x,0,1,0,e.y,0,0,1,e.z,0,0,0,1):this.set(1,0,0,e,0,1,0,t,0,0,1,n,0,0,0,1),this}makeRotationX(e){const t=Math.cos(e),n=Math.sin(e);return this.set(1,0,0,0,0,t,-n,0,0,n,t,0,0,0,0,1),this}makeRotationY(e){const t=Math.cos(e),n=Math.sin(e);return this.set(t,0,n,0,0,1,0,0,-n,0,t,0,0,0,0,1),this}makeRotationZ(e){const t=Math.cos(e),n=Math.sin(e);return this.set(t,-n,0,0,n,t,0,0,0,0,1,0,0,0,0,1),this}makeRotationAxis(e,t){const n=Math.cos(t),s=Math.sin(t),r=1-n,o=e.x,a=e.y,l=e.z,c=r*o,u=r*a;return this.set(c*o+n,c*a-s*l,c*l+s*a,0,c*a+s*l,u*a+n,u*l-s*o,0,c*l-s*a,u*l+s*o,r*l*l+n,0,0,0,0,1),this}makeScale(e,t,n){return this.set(e,0,0,0,0,t,0,0,0,0,n,0,0,0,0,1),this}makeShear(e,t,n,s,r,o){return this.set(1,n,r,0,e,1,o,0,t,s,1,0,0,0,0,1),this}compose(e,t,n){const s=this.elements,r=t._x,o=t._y,a=t._z,l=t._w,c=r+r,u=o+o,f=a+a,h=r*c,d=r*u,g=r*f,_=o*u,m=o*f,p=a*f,x=l*c,y=l*u,S=l*f,R=n.x,L=n.y,w=n.z;return s[0]=(1-(_+p))*R,s[1]=(d+S)*R,s[2]=(g-y)*R,s[3]=0,s[4]=(d-S)*L,s[5]=(1-(h+p))*L,s[6]=(m+x)*L,s[7]=0,s[8]=(g+y)*w,s[9]=(m-x)*w,s[10]=(1-(h+_))*w,s[11]=0,s[12]=e.x,s[13]=e.y,s[14]=e.z,s[15]=1,this}decompose(e,t,n){const s=this.elements;let r=Js.set(s[0],s[1],s[2]).length();const o=Js.set(s[4],s[5],s[6]).length(),a=Js.set(s[8],s[9],s[10]).length();this.determinant()<0&&(r=-r),e.x=s[12],e.y=s[13],e.z=s[14],Vn.copy(this);const c=1/r,u=1/o,f=1/a;return Vn.elements[0]*=c,Vn.elements[1]*=c,Vn.elements[2]*=c,Vn.elements[4]*=u,Vn.elements[5]*=u,Vn.elements[6]*=u,Vn.elements[8]*=f,Vn.elements[9]*=f,Vn.elements[10]*=f,t.setFromRotationMatrix(Vn),n.x=r,n.y=o,n.z=a,this}makePerspective(e,t,n,s,r,o,a=Ri){const l=this.elements,c=2*r/(t-e),u=2*r/(n-s),f=(t+e)/(t-e),h=(n+s)/(n-s);let d,g;if(a===Ri)d=-(o+r)/(o-r),g=-2*o*r/(o-r);else if(a===Xa)d=-o/(o-r),g=-o*r/(o-r);else throw new Error("THREE.Matrix4.makePerspective(): Invalid coordinate system: "+a);return l[0]=c,l[4]=0,l[8]=f,l[12]=0,l[1]=0,l[5]=u,l[9]=h,l[13]=0,l[2]=0,l[6]=0,l[10]=d,l[14]=g,l[3]=0,l[7]=0,l[11]=-1,l[15]=0,this}makeOrthographic(e,t,n,s,r,o,a=Ri){const l=this.elements,c=1/(t-e),u=1/(n-s),f=1/(o-r),h=(t+e)*c,d=(n+s)*u;let g,_;if(a===Ri)g=(o+r)*f,_=-2*f;else if(a===Xa)g=r*f,_=-1*f;else throw new Error("THREE.Matrix4.makeOrthographic(): Invalid coordinate system: "+a);return l[0]=2*c,l[4]=0,l[8]=0,l[12]=-h,l[1]=0,l[5]=2*u,l[9]=0,l[13]=-d,l[2]=0,l[6]=0,l[10]=_,l[14]=-g,l[3]=0,l[7]=0,l[11]=0,l[15]=1,this}equals(e){const t=this.elements,n=e.elements;for(let s=0;s<16;s++)if(t[s]!==n[s])return!1;return!0}fromArray(e,t=0){for(let n=0;n<16;n++)this.elements[n]=e[n+t];return this}toArray(e=[],t=0){const n=this.elements;return e[t]=n[0],e[t+1]=n[1],e[t+2]=n[2],e[t+3]=n[3],e[t+4]=n[4],e[t+5]=n[5],e[t+6]=n[6],e[t+7]=n[7],e[t+8]=n[8],e[t+9]=n[9],e[t+10]=n[10],e[t+11]=n[11],e[t+12]=n[12],e[t+13]=n[13],e[t+14]=n[14],e[t+15]=n[15],e}}const Js=new $,Vn=new Lt,sx=new $(0,0,0),rx=new $(1,1,1),ki=new $,Jo=new $,gn=new $,Mh=new Lt,Eh=new ks;class vl{constructor(e=0,t=0,n=0,s=vl.DEFAULT_ORDER){this.isEuler=!0,this._x=e,this._y=t,this._z=n,this._order=s}get x(){return this._x}set x(e){this._x=e,this._onChangeCallback()}get y(){return this._y}set y(e){this._y=e,this._onChangeCallback()}get z(){return this._z}set z(e){this._z=e,this._onChangeCallback()}get order(){return this._order}set order(e){this._order=e,this._onChangeCallback()}set(e,t,n,s=this._order){return this._x=e,this._y=t,this._z=n,this._order=s,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._order)}copy(e){return this._x=e._x,this._y=e._y,this._z=e._z,this._order=e._order,this._onChangeCallback(),this}setFromRotationMatrix(e,t=this._order,n=!0){const s=e.elements,r=s[0],o=s[4],a=s[8],l=s[1],c=s[5],u=s[9],f=s[2],h=s[6],d=s[10];switch(t){case"XYZ":this._y=Math.asin(sn(a,-1,1)),Math.abs(a)<.9999999?(this._x=Math.atan2(-u,d),this._z=Math.atan2(-o,r)):(this._x=Math.atan2(h,c),this._z=0);break;case"YXZ":this._x=Math.asin(-sn(u,-1,1)),Math.abs(u)<.9999999?(this._y=Math.atan2(a,d),this._z=Math.atan2(l,c)):(this._y=Math.atan2(-f,r),this._z=0);break;case"ZXY":this._x=Math.asin(sn(h,-1,1)),Math.abs(h)<.9999999?(this._y=Math.atan2(-f,d),this._z=Math.atan2(-o,c)):(this._y=0,this._z=Math.atan2(l,r));break;case"ZYX":this._y=Math.asin(-sn(f,-1,1)),Math.abs(f)<.9999999?(this._x=Math.atan2(h,d),this._z=Math.atan2(l,r)):(this._x=0,this._z=Math.atan2(-o,c));break;case"YZX":this._z=Math.asin(sn(l,-1,1)),Math.abs(l)<.9999999?(this._x=Math.atan2(-u,c),this._y=Math.atan2(-f,r)):(this._x=0,this._y=Math.atan2(a,d));break;case"XZY":this._z=Math.asin(-sn(o,-1,1)),Math.abs(o)<.9999999?(this._x=Math.atan2(h,c),this._y=Math.atan2(a,r)):(this._x=Math.atan2(-u,d),this._y=0);break;default:console.warn("THREE.Euler: .setFromRotationMatrix() encountered an unknown order: "+t)}return this._order=t,n===!0&&this._onChangeCallback(),this}setFromQuaternion(e,t,n){return Mh.makeRotationFromQuaternion(e),this.setFromRotationMatrix(Mh,t,n)}setFromVector3(e,t=this._order){return this.set(e.x,e.y,e.z,t)}reorder(e){return Eh.setFromEuler(this),this.setFromQuaternion(Eh,e)}equals(e){return e._x===this._x&&e._y===this._y&&e._z===this._z&&e._order===this._order}fromArray(e){return this._x=e[0],this._y=e[1],this._z=e[2],e[3]!==void 0&&(this._order=e[3]),this._onChangeCallback(),this}toArray(e=[],t=0){return e[t]=this._x,e[t+1]=this._y,e[t+2]=this._z,e[t+3]=this._order,e}_onChange(e){return this._onChangeCallback=e,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._order}}vl.DEFAULT_ORDER="XYZ";class wu{constructor(){this.mask=1}set(e){this.mask=(1<<e|0)>>>0}enable(e){this.mask|=1<<e|0}enableAll(){this.mask=-1}toggle(e){this.mask^=1<<e|0}disable(e){this.mask&=~(1<<e|0)}disableAll(){this.mask=0}test(e){return(this.mask&e.mask)!==0}isEnabled(e){return(this.mask&(1<<e|0))!==0}}let ox=0;const bh=new $,Qs=new ks,di=new Lt,Qo=new $,Yr=new $,ax=new $,lx=new ks,Th=new $(1,0,0),Ah=new $(0,1,0),wh=new $(0,0,1),cx={type:"added"},ux={type:"removed"};class Vt extends Hs{constructor(){super(),this.isObject3D=!0,Object.defineProperty(this,"id",{value:ox++}),this.uuid=Io(),this.name="",this.type="Object3D",this.parent=null,this.children=[],this.up=Vt.DEFAULT_UP.clone();const e=new $,t=new vl,n=new ks,s=new $(1,1,1);function r(){n.setFromEuler(t,!1)}function o(){t.setFromQuaternion(n,void 0,!1)}t._onChange(r),n._onChange(o),Object.defineProperties(this,{position:{configurable:!0,enumerable:!0,value:e},rotation:{configurable:!0,enumerable:!0,value:t},quaternion:{configurable:!0,enumerable:!0,value:n},scale:{configurable:!0,enumerable:!0,value:s},modelViewMatrix:{value:new Lt},normalMatrix:{value:new je}}),this.matrix=new Lt,this.matrixWorld=new Lt,this.matrixAutoUpdate=Vt.DEFAULT_MATRIX_AUTO_UPDATE,this.matrixWorldAutoUpdate=Vt.DEFAULT_MATRIX_WORLD_AUTO_UPDATE,this.matrixWorldNeedsUpdate=!1,this.layers=new wu,this.visible=!0,this.castShadow=!1,this.receiveShadow=!1,this.frustumCulled=!0,this.renderOrder=0,this.animations=[],this.userData={}}onBeforeShadow(){}onAfterShadow(){}onBeforeRender(){}onAfterRender(){}applyMatrix4(e){this.matrixAutoUpdate&&this.updateMatrix(),this.matrix.premultiply(e),this.matrix.decompose(this.position,this.quaternion,this.scale)}applyQuaternion(e){return this.quaternion.premultiply(e),this}setRotationFromAxisAngle(e,t){this.quaternion.setFromAxisAngle(e,t)}setRotationFromEuler(e){this.quaternion.setFromEuler(e,!0)}setRotationFromMatrix(e){this.quaternion.setFromRotationMatrix(e)}setRotationFromQuaternion(e){this.quaternion.copy(e)}rotateOnAxis(e,t){return Qs.setFromAxisAngle(e,t),this.quaternion.multiply(Qs),this}rotateOnWorldAxis(e,t){return Qs.setFromAxisAngle(e,t),this.quaternion.premultiply(Qs),this}rotateX(e){return this.rotateOnAxis(Th,e)}rotateY(e){return this.rotateOnAxis(Ah,e)}rotateZ(e){return this.rotateOnAxis(wh,e)}translateOnAxis(e,t){return bh.copy(e).applyQuaternion(this.quaternion),this.position.add(bh.multiplyScalar(t)),this}translateX(e){return this.translateOnAxis(Th,e)}translateY(e){return this.translateOnAxis(Ah,e)}translateZ(e){return this.translateOnAxis(wh,e)}localToWorld(e){return this.updateWorldMatrix(!0,!1),e.applyMatrix4(this.matrixWorld)}worldToLocal(e){return this.updateWorldMatrix(!0,!1),e.applyMatrix4(di.copy(this.matrixWorld).invert())}lookAt(e,t,n){e.isVector3?Qo.copy(e):Qo.set(e,t,n);const s=this.parent;this.updateWorldMatrix(!0,!1),Yr.setFromMatrixPosition(this.matrixWorld),this.isCamera||this.isLight?di.lookAt(Yr,Qo,this.up):di.lookAt(Qo,Yr,this.up),this.quaternion.setFromRotationMatrix(di),s&&(di.extractRotation(s.matrixWorld),Qs.setFromRotationMatrix(di),this.quaternion.premultiply(Qs.invert()))}add(e){if(arguments.length>1){for(let t=0;t<arguments.length;t++)this.add(arguments[t]);return this}return e===this?(console.error("THREE.Object3D.add: object can't be added as a child of itself.",e),this):(e&&e.isObject3D?(e.parent!==null&&e.parent.remove(e),e.parent=this,this.children.push(e),e.dispatchEvent(cx)):console.error("THREE.Object3D.add: object not an instance of THREE.Object3D.",e),this)}remove(e){if(arguments.length>1){for(let n=0;n<arguments.length;n++)this.remove(arguments[n]);return this}const t=this.children.indexOf(e);return t!==-1&&(e.parent=null,this.children.splice(t,1),e.dispatchEvent(ux)),this}removeFromParent(){const e=this.parent;return e!==null&&e.remove(this),this}clear(){return this.remove(...this.children)}attach(e){return this.updateWorldMatrix(!0,!1),di.copy(this.matrixWorld).invert(),e.parent!==null&&(e.parent.updateWorldMatrix(!0,!1),di.multiply(e.parent.matrixWorld)),e.applyMatrix4(di),this.add(e),e.updateWorldMatrix(!1,!0),this}getObjectById(e){return this.getObjectByProperty("id",e)}getObjectByName(e){return this.getObjectByProperty("name",e)}getObjectByProperty(e,t){if(this[e]===t)return this;for(let n=0,s=this.children.length;n<s;n++){const o=this.children[n].getObjectByProperty(e,t);if(o!==void 0)return o}}getObjectsByProperty(e,t,n=[]){this[e]===t&&n.push(this);const s=this.children;for(let r=0,o=s.length;r<o;r++)s[r].getObjectsByProperty(e,t,n);return n}getWorldPosition(e){return this.updateWorldMatrix(!0,!1),e.setFromMatrixPosition(this.matrixWorld)}getWorldQuaternion(e){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(Yr,e,ax),e}getWorldScale(e){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(Yr,lx,e),e}getWorldDirection(e){this.updateWorldMatrix(!0,!1);const t=this.matrixWorld.elements;return e.set(t[8],t[9],t[10]).normalize()}raycast(){}traverse(e){e(this);const t=this.children;for(let n=0,s=t.length;n<s;n++)t[n].traverse(e)}traverseVisible(e){if(this.visible===!1)return;e(this);const t=this.children;for(let n=0,s=t.length;n<s;n++)t[n].traverseVisible(e)}traverseAncestors(e){const t=this.parent;t!==null&&(e(t),t.traverseAncestors(e))}updateMatrix(){this.matrix.compose(this.position,this.quaternion,this.scale),this.matrixWorldNeedsUpdate=!0}updateMatrixWorld(e){this.matrixAutoUpdate&&this.updateMatrix(),(this.matrixWorldNeedsUpdate||e)&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix),this.matrixWorldNeedsUpdate=!1,e=!0);const t=this.children;for(let n=0,s=t.length;n<s;n++){const r=t[n];(r.matrixWorldAutoUpdate===!0||e===!0)&&r.updateMatrixWorld(e)}}updateWorldMatrix(e,t){const n=this.parent;if(e===!0&&n!==null&&n.matrixWorldAutoUpdate===!0&&n.updateWorldMatrix(!0,!1),this.matrixAutoUpdate&&this.updateMatrix(),this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix),t===!0){const s=this.children;for(let r=0,o=s.length;r<o;r++){const a=s[r];a.matrixWorldAutoUpdate===!0&&a.updateWorldMatrix(!1,!0)}}}toJSON(e){const t=e===void 0||typeof e=="string",n={};t&&(e={geometries:{},materials:{},textures:{},images:{},shapes:{},skeletons:{},animations:{},nodes:{}},n.metadata={version:4.6,type:"Object",generator:"Object3D.toJSON"});const s={};s.uuid=this.uuid,s.type=this.type,this.name!==""&&(s.name=this.name),this.castShadow===!0&&(s.castShadow=!0),this.receiveShadow===!0&&(s.receiveShadow=!0),this.visible===!1&&(s.visible=!1),this.frustumCulled===!1&&(s.frustumCulled=!1),this.renderOrder!==0&&(s.renderOrder=this.renderOrder),Object.keys(this.userData).length>0&&(s.userData=this.userData),s.layers=this.layers.mask,s.matrix=this.matrix.toArray(),s.up=this.up.toArray(),this.matrixAutoUpdate===!1&&(s.matrixAutoUpdate=!1),this.isInstancedMesh&&(s.type="InstancedMesh",s.count=this.count,s.instanceMatrix=this.instanceMatrix.toJSON(),this.instanceColor!==null&&(s.instanceColor=this.instanceColor.toJSON())),this.isBatchedMesh&&(s.type="BatchedMesh",s.perObjectFrustumCulled=this.perObjectFrustumCulled,s.sortObjects=this.sortObjects,s.drawRanges=this._drawRanges,s.reservedRanges=this._reservedRanges,s.visibility=this._visibility,s.active=this._active,s.bounds=this._bounds.map(a=>({boxInitialized:a.boxInitialized,boxMin:a.box.min.toArray(),boxMax:a.box.max.toArray(),sphereInitialized:a.sphereInitialized,sphereRadius:a.sphere.radius,sphereCenter:a.sphere.center.toArray()})),s.maxGeometryCount=this._maxGeometryCount,s.maxVertexCount=this._maxVertexCount,s.maxIndexCount=this._maxIndexCount,s.geometryInitialized=this._geometryInitialized,s.geometryCount=this._geometryCount,s.matricesTexture=this._matricesTexture.toJSON(e),this.boundingSphere!==null&&(s.boundingSphere={center:s.boundingSphere.center.toArray(),radius:s.boundingSphere.radius}),this.boundingBox!==null&&(s.boundingBox={min:s.boundingBox.min.toArray(),max:s.boundingBox.max.toArray()}));function r(a,l){return a[l.uuid]===void 0&&(a[l.uuid]=l.toJSON(e)),l.uuid}if(this.isScene)this.background&&(this.background.isColor?s.background=this.background.toJSON():this.background.isTexture&&(s.background=this.background.toJSON(e).uuid)),this.environment&&this.environment.isTexture&&this.environment.isRenderTargetTexture!==!0&&(s.environment=this.environment.toJSON(e).uuid);else if(this.isMesh||this.isLine||this.isPoints){s.geometry=r(e.geometries,this.geometry);const a=this.geometry.parameters;if(a!==void 0&&a.shapes!==void 0){const l=a.shapes;if(Array.isArray(l))for(let c=0,u=l.length;c<u;c++){const f=l[c];r(e.shapes,f)}else r(e.shapes,l)}}if(this.isSkinnedMesh&&(s.bindMode=this.bindMode,s.bindMatrix=this.bindMatrix.toArray(),this.skeleton!==void 0&&(r(e.skeletons,this.skeleton),s.skeleton=this.skeleton.uuid)),this.material!==void 0)if(Array.isArray(this.material)){const a=[];for(let l=0,c=this.material.length;l<c;l++)a.push(r(e.materials,this.material[l]));s.material=a}else s.material=r(e.materials,this.material);if(this.children.length>0){s.children=[];for(let a=0;a<this.children.length;a++)s.children.push(this.children[a].toJSON(e).object)}if(this.animations.length>0){s.animations=[];for(let a=0;a<this.animations.length;a++){const l=this.animations[a];s.animations.push(r(e.animations,l))}}if(t){const a=o(e.geometries),l=o(e.materials),c=o(e.textures),u=o(e.images),f=o(e.shapes),h=o(e.skeletons),d=o(e.animations),g=o(e.nodes);a.length>0&&(n.geometries=a),l.length>0&&(n.materials=l),c.length>0&&(n.textures=c),u.length>0&&(n.images=u),f.length>0&&(n.shapes=f),h.length>0&&(n.skeletons=h),d.length>0&&(n.animations=d),g.length>0&&(n.nodes=g)}return n.object=s,n;function o(a){const l=[];for(const c in a){const u=a[c];delete u.metadata,l.push(u)}return l}}clone(e){return new this.constructor().copy(this,e)}copy(e,t=!0){if(this.name=e.name,this.up.copy(e.up),this.position.copy(e.position),this.rotation.order=e.rotation.order,this.quaternion.copy(e.quaternion),this.scale.copy(e.scale),this.matrix.copy(e.matrix),this.matrixWorld.copy(e.matrixWorld),this.matrixAutoUpdate=e.matrixAutoUpdate,this.matrixWorldAutoUpdate=e.matrixWorldAutoUpdate,this.matrixWorldNeedsUpdate=e.matrixWorldNeedsUpdate,this.layers.mask=e.layers.mask,this.visible=e.visible,this.castShadow=e.castShadow,this.receiveShadow=e.receiveShadow,this.frustumCulled=e.frustumCulled,this.renderOrder=e.renderOrder,this.animations=e.animations.slice(),this.userData=JSON.parse(JSON.stringify(e.userData)),t===!0)for(let n=0;n<e.children.length;n++){const s=e.children[n];this.add(s.clone())}return this}}Vt.DEFAULT_UP=new $(0,1,0);Vt.DEFAULT_MATRIX_AUTO_UPDATE=!0;Vt.DEFAULT_MATRIX_WORLD_AUTO_UPDATE=!0;const Hn=new $,pi=new $,Ql=new $,mi=new $,er=new $,tr=new $,Rh=new $,ec=new $,tc=new $,nc=new $;let ea=!1;class Gn{constructor(e=new $,t=new $,n=new $){this.a=e,this.b=t,this.c=n}static getNormal(e,t,n,s){s.subVectors(n,t),Hn.subVectors(e,t),s.cross(Hn);const r=s.lengthSq();return r>0?s.multiplyScalar(1/Math.sqrt(r)):s.set(0,0,0)}static getBarycoord(e,t,n,s,r){Hn.subVectors(s,t),pi.subVectors(n,t),Ql.subVectors(e,t);const o=Hn.dot(Hn),a=Hn.dot(pi),l=Hn.dot(Ql),c=pi.dot(pi),u=pi.dot(Ql),f=o*c-a*a;if(f===0)return r.set(0,0,0),null;const h=1/f,d=(c*l-a*u)*h,g=(o*u-a*l)*h;return r.set(1-d-g,g,d)}static containsPoint(e,t,n,s){return this.getBarycoord(e,t,n,s,mi)===null?!1:mi.x>=0&&mi.y>=0&&mi.x+mi.y<=1}static getUV(e,t,n,s,r,o,a,l){return ea===!1&&(console.warn("THREE.Triangle.getUV() has been renamed to THREE.Triangle.getInterpolation()."),ea=!0),this.getInterpolation(e,t,n,s,r,o,a,l)}static getInterpolation(e,t,n,s,r,o,a,l){return this.getBarycoord(e,t,n,s,mi)===null?(l.x=0,l.y=0,"z"in l&&(l.z=0),"w"in l&&(l.w=0),null):(l.setScalar(0),l.addScaledVector(r,mi.x),l.addScaledVector(o,mi.y),l.addScaledVector(a,mi.z),l)}static isFrontFacing(e,t,n,s){return Hn.subVectors(n,t),pi.subVectors(e,t),Hn.cross(pi).dot(s)<0}set(e,t,n){return this.a.copy(e),this.b.copy(t),this.c.copy(n),this}setFromPointsAndIndices(e,t,n,s){return this.a.copy(e[t]),this.b.copy(e[n]),this.c.copy(e[s]),this}setFromAttributeAndIndices(e,t,n,s){return this.a.fromBufferAttribute(e,t),this.b.fromBufferAttribute(e,n),this.c.fromBufferAttribute(e,s),this}clone(){return new this.constructor().copy(this)}copy(e){return this.a.copy(e.a),this.b.copy(e.b),this.c.copy(e.c),this}getArea(){return Hn.subVectors(this.c,this.b),pi.subVectors(this.a,this.b),Hn.cross(pi).length()*.5}getMidpoint(e){return e.addVectors(this.a,this.b).add(this.c).multiplyScalar(1/3)}getNormal(e){return Gn.getNormal(this.a,this.b,this.c,e)}getPlane(e){return e.setFromCoplanarPoints(this.a,this.b,this.c)}getBarycoord(e,t){return Gn.getBarycoord(e,this.a,this.b,this.c,t)}getUV(e,t,n,s,r){return ea===!1&&(console.warn("THREE.Triangle.getUV() has been renamed to THREE.Triangle.getInterpolation()."),ea=!0),Gn.getInterpolation(e,this.a,this.b,this.c,t,n,s,r)}getInterpolation(e,t,n,s,r){return Gn.getInterpolation(e,this.a,this.b,this.c,t,n,s,r)}containsPoint(e){return Gn.containsPoint(e,this.a,this.b,this.c)}isFrontFacing(e){return Gn.isFrontFacing(this.a,this.b,this.c,e)}intersectsBox(e){return e.intersectsTriangle(this)}closestPointToPoint(e,t){const n=this.a,s=this.b,r=this.c;let o,a;er.subVectors(s,n),tr.subVectors(r,n),ec.subVectors(e,n);const l=er.dot(ec),c=tr.dot(ec);if(l<=0&&c<=0)return t.copy(n);tc.subVectors(e,s);const u=er.dot(tc),f=tr.dot(tc);if(u>=0&&f<=u)return t.copy(s);const h=l*f-u*c;if(h<=0&&l>=0&&u<=0)return o=l/(l-u),t.copy(n).addScaledVector(er,o);nc.subVectors(e,r);const d=er.dot(nc),g=tr.dot(nc);if(g>=0&&d<=g)return t.copy(r);const _=d*c-l*g;if(_<=0&&c>=0&&g<=0)return a=c/(c-g),t.copy(n).addScaledVector(tr,a);const m=u*g-d*f;if(m<=0&&f-u>=0&&d-g>=0)return Rh.subVectors(r,s),a=(f-u)/(f-u+(d-g)),t.copy(s).addScaledVector(Rh,a);const p=1/(m+_+h);return o=_*p,a=h*p,t.copy(n).addScaledVector(er,o).addScaledVector(tr,a)}equals(e){return e.a.equals(this.a)&&e.b.equals(this.b)&&e.c.equals(this.c)}}const tm={aliceblue:15792383,antiquewhite:16444375,aqua:65535,aquamarine:8388564,azure:15794175,beige:16119260,bisque:16770244,black:0,blanchedalmond:16772045,blue:255,blueviolet:9055202,brown:10824234,burlywood:14596231,cadetblue:6266528,chartreuse:8388352,chocolate:13789470,coral:16744272,cornflowerblue:6591981,cornsilk:16775388,crimson:14423100,cyan:65535,darkblue:139,darkcyan:35723,darkgoldenrod:12092939,darkgray:11119017,darkgreen:25600,darkgrey:11119017,darkkhaki:12433259,darkmagenta:9109643,darkolivegreen:5597999,darkorange:16747520,darkorchid:10040012,darkred:9109504,darksalmon:15308410,darkseagreen:9419919,darkslateblue:4734347,darkslategray:3100495,darkslategrey:3100495,darkturquoise:52945,darkviolet:9699539,deeppink:16716947,deepskyblue:49151,dimgray:6908265,dimgrey:6908265,dodgerblue:2003199,firebrick:11674146,floralwhite:16775920,forestgreen:2263842,fuchsia:16711935,gainsboro:14474460,ghostwhite:16316671,gold:16766720,goldenrod:14329120,gray:8421504,green:32768,greenyellow:11403055,grey:8421504,honeydew:15794160,hotpink:16738740,indianred:13458524,indigo:4915330,ivory:16777200,khaki:15787660,lavender:15132410,lavenderblush:16773365,lawngreen:8190976,lemonchiffon:16775885,lightblue:11393254,lightcoral:15761536,lightcyan:14745599,lightgoldenrodyellow:16448210,lightgray:13882323,lightgreen:9498256,lightgrey:13882323,lightpink:16758465,lightsalmon:16752762,lightseagreen:2142890,lightskyblue:8900346,lightslategray:7833753,lightslategrey:7833753,lightsteelblue:11584734,lightyellow:16777184,lime:65280,limegreen:3329330,linen:16445670,magenta:16711935,maroon:8388608,mediumaquamarine:6737322,mediumblue:205,mediumorchid:12211667,mediumpurple:9662683,mediumseagreen:3978097,mediumslateblue:8087790,mediumspringgreen:64154,mediumturquoise:4772300,mediumvioletred:13047173,midnightblue:1644912,mintcream:16121850,mistyrose:16770273,moccasin:16770229,navajowhite:16768685,navy:128,oldlace:16643558,olive:8421376,olivedrab:7048739,orange:16753920,orangered:16729344,orchid:14315734,palegoldenrod:15657130,palegreen:10025880,paleturquoise:11529966,palevioletred:14381203,papayawhip:16773077,peachpuff:16767673,peru:13468991,pink:16761035,plum:14524637,powderblue:11591910,purple:8388736,rebeccapurple:6697881,red:16711680,rosybrown:12357519,royalblue:4286945,saddlebrown:9127187,salmon:16416882,sandybrown:16032864,seagreen:3050327,seashell:16774638,sienna:10506797,silver:12632256,skyblue:8900331,slateblue:6970061,slategray:7372944,slategrey:7372944,snow:16775930,springgreen:65407,steelblue:4620980,tan:13808780,teal:32896,thistle:14204888,tomato:16737095,turquoise:4251856,violet:15631086,wheat:16113331,white:16777215,whitesmoke:16119285,yellow:16776960,yellowgreen:10145074},Vi={h:0,s:0,l:0},ta={h:0,s:0,l:0};function ic(i,e,t){return t<0&&(t+=1),t>1&&(t-=1),t<1/6?i+(e-i)*6*t:t<1/2?e:t<2/3?i+(e-i)*6*(2/3-t):i}class Qe{constructor(e,t,n){return this.isColor=!0,this.r=1,this.g=1,this.b=1,this.set(e,t,n)}set(e,t,n){if(t===void 0&&n===void 0){const s=e;s&&s.isColor?this.copy(s):typeof s=="number"?this.setHex(s):typeof s=="string"&&this.setStyle(s)}else this.setRGB(e,t,n);return this}setScalar(e){return this.r=e,this.g=e,this.b=e,this}setHex(e,t=kt){return e=Math.floor(e),this.r=(e>>16&255)/255,this.g=(e>>8&255)/255,this.b=(e&255)/255,at.toWorkingColorSpace(this,t),this}setRGB(e,t,n,s=at.workingColorSpace){return this.r=e,this.g=t,this.b=n,at.toWorkingColorSpace(this,s),this}setHSL(e,t,n,s=at.workingColorSpace){if(e=jv(e,1),t=sn(t,0,1),n=sn(n,0,1),t===0)this.r=this.g=this.b=n;else{const r=n<=.5?n*(1+t):n+t-n*t,o=2*n-r;this.r=ic(o,r,e+1/3),this.g=ic(o,r,e),this.b=ic(o,r,e-1/3)}return at.toWorkingColorSpace(this,s),this}setStyle(e,t=kt){function n(r){r!==void 0&&parseFloat(r)<1&&console.warn("THREE.Color: Alpha component of "+e+" will be ignored.")}let s;if(s=/^(\w+)\(([^\)]*)\)/.exec(e)){let r;const o=s[1],a=s[2];switch(o){case"rgb":case"rgba":if(r=/^\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(a))return n(r[4]),this.setRGB(Math.min(255,parseInt(r[1],10))/255,Math.min(255,parseInt(r[2],10))/255,Math.min(255,parseInt(r[3],10))/255,t);if(r=/^\s*(\d+)\%\s*,\s*(\d+)\%\s*,\s*(\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(a))return n(r[4]),this.setRGB(Math.min(100,parseInt(r[1],10))/100,Math.min(100,parseInt(r[2],10))/100,Math.min(100,parseInt(r[3],10))/100,t);break;case"hsl":case"hsla":if(r=/^\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\%\s*,\s*(\d*\.?\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(a))return n(r[4]),this.setHSL(parseFloat(r[1])/360,parseFloat(r[2])/100,parseFloat(r[3])/100,t);break;default:console.warn("THREE.Color: Unknown color model "+e)}}else if(s=/^\#([A-Fa-f\d]+)$/.exec(e)){const r=s[1],o=r.length;if(o===3)return this.setRGB(parseInt(r.charAt(0),16)/15,parseInt(r.charAt(1),16)/15,parseInt(r.charAt(2),16)/15,t);if(o===6)return this.setHex(parseInt(r,16),t);console.warn("THREE.Color: Invalid hex color "+e)}else if(e&&e.length>0)return this.setColorName(e,t);return this}setColorName(e,t=kt){const n=tm[e.toLowerCase()];return n!==void 0?this.setHex(n,t):console.warn("THREE.Color: Unknown color "+e),this}clone(){return new this.constructor(this.r,this.g,this.b)}copy(e){return this.r=e.r,this.g=e.g,this.b=e.b,this}copySRGBToLinear(e){return this.r=Mr(e.r),this.g=Mr(e.g),this.b=Mr(e.b),this}copyLinearToSRGB(e){return this.r=Xl(e.r),this.g=Xl(e.g),this.b=Xl(e.b),this}convertSRGBToLinear(){return this.copySRGBToLinear(this),this}convertLinearToSRGB(){return this.copyLinearToSRGB(this),this}getHex(e=kt){return at.fromWorkingColorSpace(Xt.copy(this),e),Math.round(sn(Xt.r*255,0,255))*65536+Math.round(sn(Xt.g*255,0,255))*256+Math.round(sn(Xt.b*255,0,255))}getHexString(e=kt){return("000000"+this.getHex(e).toString(16)).slice(-6)}getHSL(e,t=at.workingColorSpace){at.fromWorkingColorSpace(Xt.copy(this),t);const n=Xt.r,s=Xt.g,r=Xt.b,o=Math.max(n,s,r),a=Math.min(n,s,r);let l,c;const u=(a+o)/2;if(a===o)l=0,c=0;else{const f=o-a;switch(c=u<=.5?f/(o+a):f/(2-o-a),o){case n:l=(s-r)/f+(s<r?6:0);break;case s:l=(r-n)/f+2;break;case r:l=(n-s)/f+4;break}l/=6}return e.h=l,e.s=c,e.l=u,e}getRGB(e,t=at.workingColorSpace){return at.fromWorkingColorSpace(Xt.copy(this),t),e.r=Xt.r,e.g=Xt.g,e.b=Xt.b,e}getStyle(e=kt){at.fromWorkingColorSpace(Xt.copy(this),e);const t=Xt.r,n=Xt.g,s=Xt.b;return e!==kt?`color(${e} ${t.toFixed(3)} ${n.toFixed(3)} ${s.toFixed(3)})`:`rgb(${Math.round(t*255)},${Math.round(n*255)},${Math.round(s*255)})`}offsetHSL(e,t,n){return this.getHSL(Vi),this.setHSL(Vi.h+e,Vi.s+t,Vi.l+n)}add(e){return this.r+=e.r,this.g+=e.g,this.b+=e.b,this}addColors(e,t){return this.r=e.r+t.r,this.g=e.g+t.g,this.b=e.b+t.b,this}addScalar(e){return this.r+=e,this.g+=e,this.b+=e,this}sub(e){return this.r=Math.max(0,this.r-e.r),this.g=Math.max(0,this.g-e.g),this.b=Math.max(0,this.b-e.b),this}multiply(e){return this.r*=e.r,this.g*=e.g,this.b*=e.b,this}multiplyScalar(e){return this.r*=e,this.g*=e,this.b*=e,this}lerp(e,t){return this.r+=(e.r-this.r)*t,this.g+=(e.g-this.g)*t,this.b+=(e.b-this.b)*t,this}lerpColors(e,t,n){return this.r=e.r+(t.r-e.r)*n,this.g=e.g+(t.g-e.g)*n,this.b=e.b+(t.b-e.b)*n,this}lerpHSL(e,t){this.getHSL(Vi),e.getHSL(ta);const n=Gl(Vi.h,ta.h,t),s=Gl(Vi.s,ta.s,t),r=Gl(Vi.l,ta.l,t);return this.setHSL(n,s,r),this}setFromVector3(e){return this.r=e.x,this.g=e.y,this.b=e.z,this}applyMatrix3(e){const t=this.r,n=this.g,s=this.b,r=e.elements;return this.r=r[0]*t+r[3]*n+r[6]*s,this.g=r[1]*t+r[4]*n+r[7]*s,this.b=r[2]*t+r[5]*n+r[8]*s,this}equals(e){return e.r===this.r&&e.g===this.g&&e.b===this.b}fromArray(e,t=0){return this.r=e[t],this.g=e[t+1],this.b=e[t+2],this}toArray(e=[],t=0){return e[t]=this.r,e[t+1]=this.g,e[t+2]=this.b,e}fromBufferAttribute(e,t){return this.r=e.getX(t),this.g=e.getY(t),this.b=e.getZ(t),this}toJSON(){return this.getHex()}*[Symbol.iterator](){yield this.r,yield this.g,yield this.b}}const Xt=new Qe;Qe.NAMES=tm;let fx=0;class No extends Hs{constructor(){super(),this.isMaterial=!0,Object.defineProperty(this,"id",{value:fx++}),this.uuid=Io(),this.name="",this.type="Material",this.blending=Ji,this.side=ss,this.vertexColors=!1,this.opacity=1,this.transparent=!1,this.alphaHash=!1,this.blendSrc=Oc,this.blendDst=Nc,this.blendEquation=Ts,this.blendSrcAlpha=null,this.blendDstAlpha=null,this.blendEquationAlpha=null,this.blendColor=new Qe(0,0,0),this.blendAlpha=0,this.depthFunc=Va,this.depthTest=!0,this.depthWrite=!0,this.stencilWriteMask=255,this.stencilFunc=ph,this.stencilRef=0,this.stencilFuncMask=255,this.stencilFail=Ys,this.stencilZFail=Ys,this.stencilZPass=Ys,this.stencilWrite=!1,this.clippingPlanes=null,this.clipIntersection=!1,this.clipShadows=!1,this.shadowSide=null,this.colorWrite=!0,this.precision=null,this.polygonOffset=!1,this.polygonOffsetFactor=0,this.polygonOffsetUnits=0,this.dithering=!1,this.alphaToCoverage=!1,this.premultipliedAlpha=!1,this.forceSinglePass=!1,this.visible=!0,this.toneMapped=!0,this.userData={},this.version=0,this._alphaTest=0}get alphaTest(){return this._alphaTest}set alphaTest(e){this._alphaTest>0!=e>0&&this.version++,this._alphaTest=e}onBuild(){}onBeforeRender(){}onBeforeCompile(){}customProgramCacheKey(){return this.onBeforeCompile.toString()}setValues(e){if(e!==void 0)for(const t in e){const n=e[t];if(n===void 0){console.warn(`THREE.Material: parameter '${t}' has value of undefined.`);continue}const s=this[t];if(s===void 0){console.warn(`THREE.Material: '${t}' is not a property of THREE.${this.type}.`);continue}s&&s.isColor?s.set(n):s&&s.isVector3&&n&&n.isVector3?s.copy(n):this[t]=n}}toJSON(e){const t=e===void 0||typeof e=="string";t&&(e={textures:{},images:{}});const n={metadata:{version:4.6,type:"Material",generator:"Material.toJSON"}};n.uuid=this.uuid,n.type=this.type,this.name!==""&&(n.name=this.name),this.color&&this.color.isColor&&(n.color=this.color.getHex()),this.roughness!==void 0&&(n.roughness=this.roughness),this.metalness!==void 0&&(n.metalness=this.metalness),this.sheen!==void 0&&(n.sheen=this.sheen),this.sheenColor&&this.sheenColor.isColor&&(n.sheenColor=this.sheenColor.getHex()),this.sheenRoughness!==void 0&&(n.sheenRoughness=this.sheenRoughness),this.emissive&&this.emissive.isColor&&(n.emissive=this.emissive.getHex()),this.emissiveIntensity&&this.emissiveIntensity!==1&&(n.emissiveIntensity=this.emissiveIntensity),this.specular&&this.specular.isColor&&(n.specular=this.specular.getHex()),this.specularIntensity!==void 0&&(n.specularIntensity=this.specularIntensity),this.specularColor&&this.specularColor.isColor&&(n.specularColor=this.specularColor.getHex()),this.shininess!==void 0&&(n.shininess=this.shininess),this.clearcoat!==void 0&&(n.clearcoat=this.clearcoat),this.clearcoatRoughness!==void 0&&(n.clearcoatRoughness=this.clearcoatRoughness),this.clearcoatMap&&this.clearcoatMap.isTexture&&(n.clearcoatMap=this.clearcoatMap.toJSON(e).uuid),this.clearcoatRoughnessMap&&this.clearcoatRoughnessMap.isTexture&&(n.clearcoatRoughnessMap=this.clearcoatRoughnessMap.toJSON(e).uuid),this.clearcoatNormalMap&&this.clearcoatNormalMap.isTexture&&(n.clearcoatNormalMap=this.clearcoatNormalMap.toJSON(e).uuid,n.clearcoatNormalScale=this.clearcoatNormalScale.toArray()),this.iridescence!==void 0&&(n.iridescence=this.iridescence),this.iridescenceIOR!==void 0&&(n.iridescenceIOR=this.iridescenceIOR),this.iridescenceThicknessRange!==void 0&&(n.iridescenceThicknessRange=this.iridescenceThicknessRange),this.iridescenceMap&&this.iridescenceMap.isTexture&&(n.iridescenceMap=this.iridescenceMap.toJSON(e).uuid),this.iridescenceThicknessMap&&this.iridescenceThicknessMap.isTexture&&(n.iridescenceThicknessMap=this.iridescenceThicknessMap.toJSON(e).uuid),this.anisotropy!==void 0&&(n.anisotropy=this.anisotropy),this.anisotropyRotation!==void 0&&(n.anisotropyRotation=this.anisotropyRotation),this.anisotropyMap&&this.anisotropyMap.isTexture&&(n.anisotropyMap=this.anisotropyMap.toJSON(e).uuid),this.map&&this.map.isTexture&&(n.map=this.map.toJSON(e).uuid),this.matcap&&this.matcap.isTexture&&(n.matcap=this.matcap.toJSON(e).uuid),this.alphaMap&&this.alphaMap.isTexture&&(n.alphaMap=this.alphaMap.toJSON(e).uuid),this.lightMap&&this.lightMap.isTexture&&(n.lightMap=this.lightMap.toJSON(e).uuid,n.lightMapIntensity=this.lightMapIntensity),this.aoMap&&this.aoMap.isTexture&&(n.aoMap=this.aoMap.toJSON(e).uuid,n.aoMapIntensity=this.aoMapIntensity),this.bumpMap&&this.bumpMap.isTexture&&(n.bumpMap=this.bumpMap.toJSON(e).uuid,n.bumpScale=this.bumpScale),this.normalMap&&this.normalMap.isTexture&&(n.normalMap=this.normalMap.toJSON(e).uuid,n.normalMapType=this.normalMapType,n.normalScale=this.normalScale.toArray()),this.displacementMap&&this.displacementMap.isTexture&&(n.displacementMap=this.displacementMap.toJSON(e).uuid,n.displacementScale=this.displacementScale,n.displacementBias=this.displacementBias),this.roughnessMap&&this.roughnessMap.isTexture&&(n.roughnessMap=this.roughnessMap.toJSON(e).uuid),this.metalnessMap&&this.metalnessMap.isTexture&&(n.metalnessMap=this.metalnessMap.toJSON(e).uuid),this.emissiveMap&&this.emissiveMap.isTexture&&(n.emissiveMap=this.emissiveMap.toJSON(e).uuid),this.specularMap&&this.specularMap.isTexture&&(n.specularMap=this.specularMap.toJSON(e).uuid),this.specularIntensityMap&&this.specularIntensityMap.isTexture&&(n.specularIntensityMap=this.specularIntensityMap.toJSON(e).uuid),this.specularColorMap&&this.specularColorMap.isTexture&&(n.specularColorMap=this.specularColorMap.toJSON(e).uuid),this.envMap&&this.envMap.isTexture&&(n.envMap=this.envMap.toJSON(e).uuid,this.combine!==void 0&&(n.combine=this.combine)),this.envMapIntensity!==void 0&&(n.envMapIntensity=this.envMapIntensity),this.reflectivity!==void 0&&(n.reflectivity=this.reflectivity),this.refractionRatio!==void 0&&(n.refractionRatio=this.refractionRatio),this.gradientMap&&this.gradientMap.isTexture&&(n.gradientMap=this.gradientMap.toJSON(e).uuid),this.transmission!==void 0&&(n.transmission=this.transmission),this.transmissionMap&&this.transmissionMap.isTexture&&(n.transmissionMap=this.transmissionMap.toJSON(e).uuid),this.thickness!==void 0&&(n.thickness=this.thickness),this.thicknessMap&&this.thicknessMap.isTexture&&(n.thicknessMap=this.thicknessMap.toJSON(e).uuid),this.attenuationDistance!==void 0&&this.attenuationDistance!==1/0&&(n.attenuationDistance=this.attenuationDistance),this.attenuationColor!==void 0&&(n.attenuationColor=this.attenuationColor.getHex()),this.size!==void 0&&(n.size=this.size),this.shadowSide!==null&&(n.shadowSide=this.shadowSide),this.sizeAttenuation!==void 0&&(n.sizeAttenuation=this.sizeAttenuation),this.blending!==Ji&&(n.blending=this.blending),this.side!==ss&&(n.side=this.side),this.vertexColors===!0&&(n.vertexColors=!0),this.opacity<1&&(n.opacity=this.opacity),this.transparent===!0&&(n.transparent=!0),this.blendSrc!==Oc&&(n.blendSrc=this.blendSrc),this.blendDst!==Nc&&(n.blendDst=this.blendDst),this.blendEquation!==Ts&&(n.blendEquation=this.blendEquation),this.blendSrcAlpha!==null&&(n.blendSrcAlpha=this.blendSrcAlpha),this.blendDstAlpha!==null&&(n.blendDstAlpha=this.blendDstAlpha),this.blendEquationAlpha!==null&&(n.blendEquationAlpha=this.blendEquationAlpha),this.blendColor&&this.blendColor.isColor&&(n.blendColor=this.blendColor.getHex()),this.blendAlpha!==0&&(n.blendAlpha=this.blendAlpha),this.depthFunc!==Va&&(n.depthFunc=this.depthFunc),this.depthTest===!1&&(n.depthTest=this.depthTest),this.depthWrite===!1&&(n.depthWrite=this.depthWrite),this.colorWrite===!1&&(n.colorWrite=this.colorWrite),this.stencilWriteMask!==255&&(n.stencilWriteMask=this.stencilWriteMask),this.stencilFunc!==ph&&(n.stencilFunc=this.stencilFunc),this.stencilRef!==0&&(n.stencilRef=this.stencilRef),this.stencilFuncMask!==255&&(n.stencilFuncMask=this.stencilFuncMask),this.stencilFail!==Ys&&(n.stencilFail=this.stencilFail),this.stencilZFail!==Ys&&(n.stencilZFail=this.stencilZFail),this.stencilZPass!==Ys&&(n.stencilZPass=this.stencilZPass),this.stencilWrite===!0&&(n.stencilWrite=this.stencilWrite),this.rotation!==void 0&&this.rotation!==0&&(n.rotation=this.rotation),this.polygonOffset===!0&&(n.polygonOffset=!0),this.polygonOffsetFactor!==0&&(n.polygonOffsetFactor=this.polygonOffsetFactor),this.polygonOffsetUnits!==0&&(n.polygonOffsetUnits=this.polygonOffsetUnits),this.linewidth!==void 0&&this.linewidth!==1&&(n.linewidth=this.linewidth),this.dashSize!==void 0&&(n.dashSize=this.dashSize),this.gapSize!==void 0&&(n.gapSize=this.gapSize),this.scale!==void 0&&(n.scale=this.scale),this.dithering===!0&&(n.dithering=!0),this.alphaTest>0&&(n.alphaTest=this.alphaTest),this.alphaHash===!0&&(n.alphaHash=!0),this.alphaToCoverage===!0&&(n.alphaToCoverage=!0),this.premultipliedAlpha===!0&&(n.premultipliedAlpha=!0),this.forceSinglePass===!0&&(n.forceSinglePass=!0),this.wireframe===!0&&(n.wireframe=!0),this.wireframeLinewidth>1&&(n.wireframeLinewidth=this.wireframeLinewidth),this.wireframeLinecap!=="round"&&(n.wireframeLinecap=this.wireframeLinecap),this.wireframeLinejoin!=="round"&&(n.wireframeLinejoin=this.wireframeLinejoin),this.flatShading===!0&&(n.flatShading=!0),this.visible===!1&&(n.visible=!1),this.toneMapped===!1&&(n.toneMapped=!1),this.fog===!1&&(n.fog=!1),Object.keys(this.userData).length>0&&(n.userData=this.userData);function s(r){const o=[];for(const a in r){const l=r[a];delete l.metadata,o.push(l)}return o}if(t){const r=s(e.textures),o=s(e.images);r.length>0&&(n.textures=r),o.length>0&&(n.images=o)}return n}clone(){return new this.constructor().copy(this)}copy(e){this.name=e.name,this.blending=e.blending,this.side=e.side,this.vertexColors=e.vertexColors,this.opacity=e.opacity,this.transparent=e.transparent,this.blendSrc=e.blendSrc,this.blendDst=e.blendDst,this.blendEquation=e.blendEquation,this.blendSrcAlpha=e.blendSrcAlpha,this.blendDstAlpha=e.blendDstAlpha,this.blendEquationAlpha=e.blendEquationAlpha,this.blendColor.copy(e.blendColor),this.blendAlpha=e.blendAlpha,this.depthFunc=e.depthFunc,this.depthTest=e.depthTest,this.depthWrite=e.depthWrite,this.stencilWriteMask=e.stencilWriteMask,this.stencilFunc=e.stencilFunc,this.stencilRef=e.stencilRef,this.stencilFuncMask=e.stencilFuncMask,this.stencilFail=e.stencilFail,this.stencilZFail=e.stencilZFail,this.stencilZPass=e.stencilZPass,this.stencilWrite=e.stencilWrite;const t=e.clippingPlanes;let n=null;if(t!==null){const s=t.length;n=new Array(s);for(let r=0;r!==s;++r)n[r]=t[r].clone()}return this.clippingPlanes=n,this.clipIntersection=e.clipIntersection,this.clipShadows=e.clipShadows,this.shadowSide=e.shadowSide,this.colorWrite=e.colorWrite,this.precision=e.precision,this.polygonOffset=e.polygonOffset,this.polygonOffsetFactor=e.polygonOffsetFactor,this.polygonOffsetUnits=e.polygonOffsetUnits,this.dithering=e.dithering,this.alphaTest=e.alphaTest,this.alphaHash=e.alphaHash,this.alphaToCoverage=e.alphaToCoverage,this.premultipliedAlpha=e.premultipliedAlpha,this.forceSinglePass=e.forceSinglePass,this.visible=e.visible,this.toneMapped=e.toneMapped,this.userData=JSON.parse(JSON.stringify(e.userData)),this}dispose(){this.dispatchEvent({type:"dispose"})}set needsUpdate(e){e===!0&&this.version++}}class nm extends No{constructor(e){super(),this.isMeshBasicMaterial=!0,this.type="MeshBasicMaterial",this.color=new Qe(16777215),this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.specularMap=null,this.alphaMap=null,this.envMap=null,this.combine=kp,this.reflectivity=1,this.refractionRatio=.98,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.color.copy(e.color),this.map=e.map,this.lightMap=e.lightMap,this.lightMapIntensity=e.lightMapIntensity,this.aoMap=e.aoMap,this.aoMapIntensity=e.aoMapIntensity,this.specularMap=e.specularMap,this.alphaMap=e.alphaMap,this.envMap=e.envMap,this.combine=e.combine,this.reflectivity=e.reflectivity,this.refractionRatio=e.refractionRatio,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.wireframeLinecap=e.wireframeLinecap,this.wireframeLinejoin=e.wireframeLinejoin,this.fog=e.fog,this}}const Ct=new $,na=new He;class Bn{constructor(e,t,n=!1){if(Array.isArray(e))throw new TypeError("THREE.BufferAttribute: array should be a Typed Array.");this.isBufferAttribute=!0,this.name="",this.array=e,this.itemSize=t,this.count=e!==void 0?e.length/t:0,this.normalized=n,this.usage=mh,this._updateRange={offset:0,count:-1},this.updateRanges=[],this.gpuType=qi,this.version=0}onUploadCallback(){}set needsUpdate(e){e===!0&&this.version++}get updateRange(){return console.warn("THREE.BufferAttribute: updateRange() is deprecated and will be removed in r169. Use addUpdateRange() instead."),this._updateRange}setUsage(e){return this.usage=e,this}addUpdateRange(e,t){this.updateRanges.push({start:e,count:t})}clearUpdateRanges(){this.updateRanges.length=0}copy(e){return this.name=e.name,this.array=new e.array.constructor(e.array),this.itemSize=e.itemSize,this.count=e.count,this.normalized=e.normalized,this.usage=e.usage,this.gpuType=e.gpuType,this}copyAt(e,t,n){e*=this.itemSize,n*=t.itemSize;for(let s=0,r=this.itemSize;s<r;s++)this.array[e+s]=t.array[n+s];return this}copyArray(e){return this.array.set(e),this}applyMatrix3(e){if(this.itemSize===2)for(let t=0,n=this.count;t<n;t++)na.fromBufferAttribute(this,t),na.applyMatrix3(e),this.setXY(t,na.x,na.y);else if(this.itemSize===3)for(let t=0,n=this.count;t<n;t++)Ct.fromBufferAttribute(this,t),Ct.applyMatrix3(e),this.setXYZ(t,Ct.x,Ct.y,Ct.z);return this}applyMatrix4(e){for(let t=0,n=this.count;t<n;t++)Ct.fromBufferAttribute(this,t),Ct.applyMatrix4(e),this.setXYZ(t,Ct.x,Ct.y,Ct.z);return this}applyNormalMatrix(e){for(let t=0,n=this.count;t<n;t++)Ct.fromBufferAttribute(this,t),Ct.applyNormalMatrix(e),this.setXYZ(t,Ct.x,Ct.y,Ct.z);return this}transformDirection(e){for(let t=0,n=this.count;t<n;t++)Ct.fromBufferAttribute(this,t),Ct.transformDirection(e),this.setXYZ(t,Ct.x,Ct.y,Ct.z);return this}set(e,t=0){return this.array.set(e,t),this}getComponent(e,t){let n=this.array[e*this.itemSize+t];return this.normalized&&(n=Wr(n,this.array)),n}setComponent(e,t,n){return this.normalized&&(n=on(n,this.array)),this.array[e*this.itemSize+t]=n,this}getX(e){let t=this.array[e*this.itemSize];return this.normalized&&(t=Wr(t,this.array)),t}setX(e,t){return this.normalized&&(t=on(t,this.array)),this.array[e*this.itemSize]=t,this}getY(e){let t=this.array[e*this.itemSize+1];return this.normalized&&(t=Wr(t,this.array)),t}setY(e,t){return this.normalized&&(t=on(t,this.array)),this.array[e*this.itemSize+1]=t,this}getZ(e){let t=this.array[e*this.itemSize+2];return this.normalized&&(t=Wr(t,this.array)),t}setZ(e,t){return this.normalized&&(t=on(t,this.array)),this.array[e*this.itemSize+2]=t,this}getW(e){let t=this.array[e*this.itemSize+3];return this.normalized&&(t=Wr(t,this.array)),t}setW(e,t){return this.normalized&&(t=on(t,this.array)),this.array[e*this.itemSize+3]=t,this}setXY(e,t,n){return e*=this.itemSize,this.normalized&&(t=on(t,this.array),n=on(n,this.array)),this.array[e+0]=t,this.array[e+1]=n,this}setXYZ(e,t,n,s){return e*=this.itemSize,this.normalized&&(t=on(t,this.array),n=on(n,this.array),s=on(s,this.array)),this.array[e+0]=t,this.array[e+1]=n,this.array[e+2]=s,this}setXYZW(e,t,n,s,r){return e*=this.itemSize,this.normalized&&(t=on(t,this.array),n=on(n,this.array),s=on(s,this.array),r=on(r,this.array)),this.array[e+0]=t,this.array[e+1]=n,this.array[e+2]=s,this.array[e+3]=r,this}onUpload(e){return this.onUploadCallback=e,this}clone(){return new this.constructor(this.array,this.itemSize).copy(this)}toJSON(){const e={itemSize:this.itemSize,type:this.array.constructor.name,array:Array.from(this.array),normalized:this.normalized};return this.name!==""&&(e.name=this.name),this.usage!==mh&&(e.usage=this.usage),e}}class im extends Bn{constructor(e,t,n){super(new Uint16Array(e),t,n)}}class sm extends Bn{constructor(e,t,n){super(new Uint32Array(e),t,n)}}class Is extends Bn{constructor(e,t,n){super(new Float32Array(e),t,n)}}let hx=0;const Pn=new Lt,sc=new Vt,nr=new $,vn=new Oo,$r=new Oo,Ot=new $;class Ni extends Hs{constructor(){super(),this.isBufferGeometry=!0,Object.defineProperty(this,"id",{value:hx++}),this.uuid=Io(),this.name="",this.type="BufferGeometry",this.index=null,this.attributes={},this.morphAttributes={},this.morphTargetsRelative=!1,this.groups=[],this.boundingBox=null,this.boundingSphere=null,this.drawRange={start:0,count:1/0},this.userData={}}getIndex(){return this.index}setIndex(e){return Array.isArray(e)?this.index=new(Zp(e)?sm:im)(e,1):this.index=e,this}getAttribute(e){return this.attributes[e]}setAttribute(e,t){return this.attributes[e]=t,this}deleteAttribute(e){return delete this.attributes[e],this}hasAttribute(e){return this.attributes[e]!==void 0}addGroup(e,t,n=0){this.groups.push({start:e,count:t,materialIndex:n})}clearGroups(){this.groups=[]}setDrawRange(e,t){this.drawRange.start=e,this.drawRange.count=t}applyMatrix4(e){const t=this.attributes.position;t!==void 0&&(t.applyMatrix4(e),t.needsUpdate=!0);const n=this.attributes.normal;if(n!==void 0){const r=new je().getNormalMatrix(e);n.applyNormalMatrix(r),n.needsUpdate=!0}const s=this.attributes.tangent;return s!==void 0&&(s.transformDirection(e),s.needsUpdate=!0),this.boundingBox!==null&&this.computeBoundingBox(),this.boundingSphere!==null&&this.computeBoundingSphere(),this}applyQuaternion(e){return Pn.makeRotationFromQuaternion(e),this.applyMatrix4(Pn),this}rotateX(e){return Pn.makeRotationX(e),this.applyMatrix4(Pn),this}rotateY(e){return Pn.makeRotationY(e),this.applyMatrix4(Pn),this}rotateZ(e){return Pn.makeRotationZ(e),this.applyMatrix4(Pn),this}translate(e,t,n){return Pn.makeTranslation(e,t,n),this.applyMatrix4(Pn),this}scale(e,t,n){return Pn.makeScale(e,t,n),this.applyMatrix4(Pn),this}lookAt(e){return sc.lookAt(e),sc.updateMatrix(),this.applyMatrix4(sc.matrix),this}center(){return this.computeBoundingBox(),this.boundingBox.getCenter(nr).negate(),this.translate(nr.x,nr.y,nr.z),this}setFromPoints(e){const t=[];for(let n=0,s=e.length;n<s;n++){const r=e[n];t.push(r.x,r.y,r.z||0)}return this.setAttribute("position",new Is(t,3)),this}computeBoundingBox(){this.boundingBox===null&&(this.boundingBox=new Oo);const e=this.attributes.position,t=this.morphAttributes.position;if(e&&e.isGLBufferAttribute){console.error('THREE.BufferGeometry.computeBoundingBox(): GLBufferAttribute requires a manual bounding box. Alternatively set "mesh.frustumCulled" to "false".',this),this.boundingBox.set(new $(-1/0,-1/0,-1/0),new $(1/0,1/0,1/0));return}if(e!==void 0){if(this.boundingBox.setFromBufferAttribute(e),t)for(let n=0,s=t.length;n<s;n++){const r=t[n];vn.setFromBufferAttribute(r),this.morphTargetsRelative?(Ot.addVectors(this.boundingBox.min,vn.min),this.boundingBox.expandByPoint(Ot),Ot.addVectors(this.boundingBox.max,vn.max),this.boundingBox.expandByPoint(Ot)):(this.boundingBox.expandByPoint(vn.min),this.boundingBox.expandByPoint(vn.max))}}else this.boundingBox.makeEmpty();(isNaN(this.boundingBox.min.x)||isNaN(this.boundingBox.min.y)||isNaN(this.boundingBox.min.z))&&console.error('THREE.BufferGeometry.computeBoundingBox(): Computed min/max have NaN values. The "position" attribute is likely to have NaN values.',this)}computeBoundingSphere(){this.boundingSphere===null&&(this.boundingSphere=new _l);const e=this.attributes.position,t=this.morphAttributes.position;if(e&&e.isGLBufferAttribute){console.error('THREE.BufferGeometry.computeBoundingSphere(): GLBufferAttribute requires a manual bounding sphere. Alternatively set "mesh.frustumCulled" to "false".',this),this.boundingSphere.set(new $,1/0);return}if(e){const n=this.boundingSphere.center;if(vn.setFromBufferAttribute(e),t)for(let r=0,o=t.length;r<o;r++){const a=t[r];$r.setFromBufferAttribute(a),this.morphTargetsRelative?(Ot.addVectors(vn.min,$r.min),vn.expandByPoint(Ot),Ot.addVectors(vn.max,$r.max),vn.expandByPoint(Ot)):(vn.expandByPoint($r.min),vn.expandByPoint($r.max))}vn.getCenter(n);let s=0;for(let r=0,o=e.count;r<o;r++)Ot.fromBufferAttribute(e,r),s=Math.max(s,n.distanceToSquared(Ot));if(t)for(let r=0,o=t.length;r<o;r++){const a=t[r],l=this.morphTargetsRelative;for(let c=0,u=a.count;c<u;c++)Ot.fromBufferAttribute(a,c),l&&(nr.fromBufferAttribute(e,c),Ot.add(nr)),s=Math.max(s,n.distanceToSquared(Ot))}this.boundingSphere.radius=Math.sqrt(s),isNaN(this.boundingSphere.radius)&&console.error('THREE.BufferGeometry.computeBoundingSphere(): Computed radius is NaN. The "position" attribute is likely to have NaN values.',this)}}computeTangents(){const e=this.index,t=this.attributes;if(e===null||t.position===void 0||t.normal===void 0||t.uv===void 0){console.error("THREE.BufferGeometry: .computeTangents() failed. Missing required attributes (index, position, normal or uv)");return}const n=e.array,s=t.position.array,r=t.normal.array,o=t.uv.array,a=s.length/3;this.hasAttribute("tangent")===!1&&this.setAttribute("tangent",new Bn(new Float32Array(4*a),4));const l=this.getAttribute("tangent").array,c=[],u=[];for(let b=0;b<a;b++)c[b]=new $,u[b]=new $;const f=new $,h=new $,d=new $,g=new He,_=new He,m=new He,p=new $,x=new $;function y(b,N,A){f.fromArray(s,b*3),h.fromArray(s,N*3),d.fromArray(s,A*3),g.fromArray(o,b*2),_.fromArray(o,N*2),m.fromArray(o,A*2),h.sub(f),d.sub(f),_.sub(g),m.sub(g);const I=1/(_.x*m.y-m.x*_.y);isFinite(I)&&(p.copy(h).multiplyScalar(m.y).addScaledVector(d,-_.y).multiplyScalar(I),x.copy(d).multiplyScalar(_.x).addScaledVector(h,-m.x).multiplyScalar(I),c[b].add(p),c[N].add(p),c[A].add(p),u[b].add(x),u[N].add(x),u[A].add(x))}let S=this.groups;S.length===0&&(S=[{start:0,count:n.length}]);for(let b=0,N=S.length;b<N;++b){const A=S[b],I=A.start,O=A.count;for(let k=I,H=I+O;k<H;k+=3)y(n[k+0],n[k+1],n[k+2])}const R=new $,L=new $,w=new $,B=new $;function v(b){w.fromArray(r,b*3),B.copy(w);const N=c[b];R.copy(N),R.sub(w.multiplyScalar(w.dot(N))).normalize(),L.crossVectors(B,N);const I=L.dot(u[b])<0?-1:1;l[b*4]=R.x,l[b*4+1]=R.y,l[b*4+2]=R.z,l[b*4+3]=I}for(let b=0,N=S.length;b<N;++b){const A=S[b],I=A.start,O=A.count;for(let k=I,H=I+O;k<H;k+=3)v(n[k+0]),v(n[k+1]),v(n[k+2])}}computeVertexNormals(){const e=this.index,t=this.getAttribute("position");if(t!==void 0){let n=this.getAttribute("normal");if(n===void 0)n=new Bn(new Float32Array(t.count*3),3),this.setAttribute("normal",n);else for(let h=0,d=n.count;h<d;h++)n.setXYZ(h,0,0,0);const s=new $,r=new $,o=new $,a=new $,l=new $,c=new $,u=new $,f=new $;if(e)for(let h=0,d=e.count;h<d;h+=3){const g=e.getX(h+0),_=e.getX(h+1),m=e.getX(h+2);s.fromBufferAttribute(t,g),r.fromBufferAttribute(t,_),o.fromBufferAttribute(t,m),u.subVectors(o,r),f.subVectors(s,r),u.cross(f),a.fromBufferAttribute(n,g),l.fromBufferAttribute(n,_),c.fromBufferAttribute(n,m),a.add(u),l.add(u),c.add(u),n.setXYZ(g,a.x,a.y,a.z),n.setXYZ(_,l.x,l.y,l.z),n.setXYZ(m,c.x,c.y,c.z)}else for(let h=0,d=t.count;h<d;h+=3)s.fromBufferAttribute(t,h+0),r.fromBufferAttribute(t,h+1),o.fromBufferAttribute(t,h+2),u.subVectors(o,r),f.subVectors(s,r),u.cross(f),n.setXYZ(h+0,u.x,u.y,u.z),n.setXYZ(h+1,u.x,u.y,u.z),n.setXYZ(h+2,u.x,u.y,u.z);this.normalizeNormals(),n.needsUpdate=!0}}normalizeNormals(){const e=this.attributes.normal;for(let t=0,n=e.count;t<n;t++)Ot.fromBufferAttribute(e,t),Ot.normalize(),e.setXYZ(t,Ot.x,Ot.y,Ot.z)}toNonIndexed(){function e(a,l){const c=a.array,u=a.itemSize,f=a.normalized,h=new c.constructor(l.length*u);let d=0,g=0;for(let _=0,m=l.length;_<m;_++){a.isInterleavedBufferAttribute?d=l[_]*a.data.stride+a.offset:d=l[_]*u;for(let p=0;p<u;p++)h[g++]=c[d++]}return new Bn(h,u,f)}if(this.index===null)return console.warn("THREE.BufferGeometry.toNonIndexed(): BufferGeometry is already non-indexed."),this;const t=new Ni,n=this.index.array,s=this.attributes;for(const a in s){const l=s[a],c=e(l,n);t.setAttribute(a,c)}const r=this.morphAttributes;for(const a in r){const l=[],c=r[a];for(let u=0,f=c.length;u<f;u++){const h=c[u],d=e(h,n);l.push(d)}t.morphAttributes[a]=l}t.morphTargetsRelative=this.morphTargetsRelative;const o=this.groups;for(let a=0,l=o.length;a<l;a++){const c=o[a];t.addGroup(c.start,c.count,c.materialIndex)}return t}toJSON(){const e={metadata:{version:4.6,type:"BufferGeometry",generator:"BufferGeometry.toJSON"}};if(e.uuid=this.uuid,e.type=this.type,this.name!==""&&(e.name=this.name),Object.keys(this.userData).length>0&&(e.userData=this.userData),this.parameters!==void 0){const l=this.parameters;for(const c in l)l[c]!==void 0&&(e[c]=l[c]);return e}e.data={attributes:{}};const t=this.index;t!==null&&(e.data.index={type:t.array.constructor.name,array:Array.prototype.slice.call(t.array)});const n=this.attributes;for(const l in n){const c=n[l];e.data.attributes[l]=c.toJSON(e.data)}const s={};let r=!1;for(const l in this.morphAttributes){const c=this.morphAttributes[l],u=[];for(let f=0,h=c.length;f<h;f++){const d=c[f];u.push(d.toJSON(e.data))}u.length>0&&(s[l]=u,r=!0)}r&&(e.data.morphAttributes=s,e.data.morphTargetsRelative=this.morphTargetsRelative);const o=this.groups;o.length>0&&(e.data.groups=JSON.parse(JSON.stringify(o)));const a=this.boundingSphere;return a!==null&&(e.data.boundingSphere={center:a.center.toArray(),radius:a.radius}),e}clone(){return new this.constructor().copy(this)}copy(e){this.index=null,this.attributes={},this.morphAttributes={},this.groups=[],this.boundingBox=null,this.boundingSphere=null;const t={};this.name=e.name;const n=e.index;n!==null&&this.setIndex(n.clone(t));const s=e.attributes;for(const c in s){const u=s[c];this.setAttribute(c,u.clone(t))}const r=e.morphAttributes;for(const c in r){const u=[],f=r[c];for(let h=0,d=f.length;h<d;h++)u.push(f[h].clone(t));this.morphAttributes[c]=u}this.morphTargetsRelative=e.morphTargetsRelative;const o=e.groups;for(let c=0,u=o.length;c<u;c++){const f=o[c];this.addGroup(f.start,f.count,f.materialIndex)}const a=e.boundingBox;a!==null&&(this.boundingBox=a.clone());const l=e.boundingSphere;return l!==null&&(this.boundingSphere=l.clone()),this.drawRange.start=e.drawRange.start,this.drawRange.count=e.drawRange.count,this.userData=e.userData,this}dispose(){this.dispatchEvent({type:"dispose"})}}const Ch=new Lt,gs=new gl,ia=new _l,Ph=new $,ir=new $,sr=new $,rr=new $,rc=new $,sa=new $,ra=new He,oa=new He,aa=new He,Lh=new $,Dh=new $,Uh=new $,la=new $,ca=new $;class Yi extends Vt{constructor(e=new Ni,t=new nm){super(),this.isMesh=!0,this.type="Mesh",this.geometry=e,this.material=t,this.updateMorphTargets()}copy(e,t){return super.copy(e,t),e.morphTargetInfluences!==void 0&&(this.morphTargetInfluences=e.morphTargetInfluences.slice()),e.morphTargetDictionary!==void 0&&(this.morphTargetDictionary=Object.assign({},e.morphTargetDictionary)),this.material=Array.isArray(e.material)?e.material.slice():e.material,this.geometry=e.geometry,this}updateMorphTargets(){const t=this.geometry.morphAttributes,n=Object.keys(t);if(n.length>0){const s=t[n[0]];if(s!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let r=0,o=s.length;r<o;r++){const a=s[r].name||String(r);this.morphTargetInfluences.push(0),this.morphTargetDictionary[a]=r}}}}getVertexPosition(e,t){const n=this.geometry,s=n.attributes.position,r=n.morphAttributes.position,o=n.morphTargetsRelative;t.fromBufferAttribute(s,e);const a=this.morphTargetInfluences;if(r&&a){sa.set(0,0,0);for(let l=0,c=r.length;l<c;l++){const u=a[l],f=r[l];u!==0&&(rc.fromBufferAttribute(f,e),o?sa.addScaledVector(rc,u):sa.addScaledVector(rc.sub(t),u))}t.add(sa)}return t}raycast(e,t){const n=this.geometry,s=this.material,r=this.matrixWorld;s!==void 0&&(n.boundingSphere===null&&n.computeBoundingSphere(),ia.copy(n.boundingSphere),ia.applyMatrix4(r),gs.copy(e.ray).recast(e.near),!(ia.containsPoint(gs.origin)===!1&&(gs.intersectSphere(ia,Ph)===null||gs.origin.distanceToSquared(Ph)>(e.far-e.near)**2))&&(Ch.copy(r).invert(),gs.copy(e.ray).applyMatrix4(Ch),!(n.boundingBox!==null&&gs.intersectsBox(n.boundingBox)===!1)&&this._computeIntersections(e,t,gs)))}_computeIntersections(e,t,n){let s;const r=this.geometry,o=this.material,a=r.index,l=r.attributes.position,c=r.attributes.uv,u=r.attributes.uv1,f=r.attributes.normal,h=r.groups,d=r.drawRange;if(a!==null)if(Array.isArray(o))for(let g=0,_=h.length;g<_;g++){const m=h[g],p=o[m.materialIndex],x=Math.max(m.start,d.start),y=Math.min(a.count,Math.min(m.start+m.count,d.start+d.count));for(let S=x,R=y;S<R;S+=3){const L=a.getX(S),w=a.getX(S+1),B=a.getX(S+2);s=ua(this,p,e,n,c,u,f,L,w,B),s&&(s.faceIndex=Math.floor(S/3),s.face.materialIndex=m.materialIndex,t.push(s))}}else{const g=Math.max(0,d.start),_=Math.min(a.count,d.start+d.count);for(let m=g,p=_;m<p;m+=3){const x=a.getX(m),y=a.getX(m+1),S=a.getX(m+2);s=ua(this,o,e,n,c,u,f,x,y,S),s&&(s.faceIndex=Math.floor(m/3),t.push(s))}}else if(l!==void 0)if(Array.isArray(o))for(let g=0,_=h.length;g<_;g++){const m=h[g],p=o[m.materialIndex],x=Math.max(m.start,d.start),y=Math.min(l.count,Math.min(m.start+m.count,d.start+d.count));for(let S=x,R=y;S<R;S+=3){const L=S,w=S+1,B=S+2;s=ua(this,p,e,n,c,u,f,L,w,B),s&&(s.faceIndex=Math.floor(S/3),s.face.materialIndex=m.materialIndex,t.push(s))}}else{const g=Math.max(0,d.start),_=Math.min(l.count,d.start+d.count);for(let m=g,p=_;m<p;m+=3){const x=m,y=m+1,S=m+2;s=ua(this,o,e,n,c,u,f,x,y,S),s&&(s.faceIndex=Math.floor(m/3),t.push(s))}}}}function dx(i,e,t,n,s,r,o,a){let l;if(e.side===un?l=n.intersectTriangle(o,r,s,!0,a):l=n.intersectTriangle(s,r,o,e.side===ss,a),l===null)return null;ca.copy(a),ca.applyMatrix4(i.matrixWorld);const c=t.ray.origin.distanceTo(ca);return c<t.near||c>t.far?null:{distance:c,point:ca.clone(),object:i}}function ua(i,e,t,n,s,r,o,a,l,c){i.getVertexPosition(a,ir),i.getVertexPosition(l,sr),i.getVertexPosition(c,rr);const u=dx(i,e,t,n,ir,sr,rr,la);if(u){s&&(ra.fromBufferAttribute(s,a),oa.fromBufferAttribute(s,l),aa.fromBufferAttribute(s,c),u.uv=Gn.getInterpolation(la,ir,sr,rr,ra,oa,aa,new He)),r&&(ra.fromBufferAttribute(r,a),oa.fromBufferAttribute(r,l),aa.fromBufferAttribute(r,c),u.uv1=Gn.getInterpolation(la,ir,sr,rr,ra,oa,aa,new He),u.uv2=u.uv1),o&&(Lh.fromBufferAttribute(o,a),Dh.fromBufferAttribute(o,l),Uh.fromBufferAttribute(o,c),u.normal=Gn.getInterpolation(la,ir,sr,rr,Lh,Dh,Uh,new $),u.normal.dot(n.direction)>0&&u.normal.multiplyScalar(-1));const f={a,b:l,c,normal:new $,materialIndex:0};Gn.getNormal(ir,sr,rr,f.normal),u.face=f}return u}class Fo extends Ni{constructor(e=1,t=1,n=1,s=1,r=1,o=1){super(),this.type="BoxGeometry",this.parameters={width:e,height:t,depth:n,widthSegments:s,heightSegments:r,depthSegments:o};const a=this;s=Math.floor(s),r=Math.floor(r),o=Math.floor(o);const l=[],c=[],u=[],f=[];let h=0,d=0;g("z","y","x",-1,-1,n,t,e,o,r,0),g("z","y","x",1,-1,n,t,-e,o,r,1),g("x","z","y",1,1,e,n,t,s,o,2),g("x","z","y",1,-1,e,n,-t,s,o,3),g("x","y","z",1,-1,e,t,n,s,r,4),g("x","y","z",-1,-1,e,t,-n,s,r,5),this.setIndex(l),this.setAttribute("position",new Is(c,3)),this.setAttribute("normal",new Is(u,3)),this.setAttribute("uv",new Is(f,2));function g(_,m,p,x,y,S,R,L,w,B,v){const b=S/w,N=R/B,A=S/2,I=R/2,O=L/2,k=w+1,H=B+1;let q=0,Z=0;const W=new $;for(let j=0;j<H;j++){const G=j*N-I;for(let re=0;re<k;re++){const Q=re*b-A;W[_]=Q*x,W[m]=G*y,W[p]=O,c.push(W.x,W.y,W.z),W[_]=0,W[m]=0,W[p]=L>0?1:-1,u.push(W.x,W.y,W.z),f.push(re/w),f.push(1-j/B),q+=1}}for(let j=0;j<B;j++)for(let G=0;G<w;G++){const re=h+G+k*j,Q=h+G+k*(j+1),le=h+(G+1)+k*(j+1),_e=h+(G+1)+k*j;l.push(re,Q,_e),l.push(Q,le,_e),Z+=6}a.addGroup(d,Z,v),d+=Z,h+=q}}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new Fo(e.width,e.height,e.depth,e.widthSegments,e.heightSegments,e.depthSegments)}}function Lr(i){const e={};for(const t in i){e[t]={};for(const n in i[t]){const s=i[t][n];s&&(s.isColor||s.isMatrix3||s.isMatrix4||s.isVector2||s.isVector3||s.isVector4||s.isTexture||s.isQuaternion)?s.isRenderTargetTexture?(console.warn("UniformsUtils: Textures of render targets cannot be cloned via cloneUniforms() or mergeUniforms()."),e[t][n]=null):e[t][n]=s.clone():Array.isArray(s)?e[t][n]=s.slice():e[t][n]=s}}return e}function Qt(i){const e={};for(let t=0;t<i.length;t++){const n=Lr(i[t]);for(const s in n)e[s]=n[s]}return e}function px(i){const e=[];for(let t=0;t<i.length;t++)e.push(i[t].clone());return e}function rm(i){return i.getRenderTarget()===null?i.outputColorSpace:at.workingColorSpace}const mx={clone:Lr,merge:Qt};var _x=`void main() {
	gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
}`,gx=`void main() {
	gl_FragColor = vec4( 1.0, 0.0, 0.0, 1.0 );
}`;class rs extends No{constructor(e){super(),this.isShaderMaterial=!0,this.type="ShaderMaterial",this.defines={},this.uniforms={},this.uniformsGroups=[],this.vertexShader=_x,this.fragmentShader=gx,this.linewidth=1,this.wireframe=!1,this.wireframeLinewidth=1,this.fog=!1,this.lights=!1,this.clipping=!1,this.forceSinglePass=!0,this.extensions={derivatives:!1,fragDepth:!1,drawBuffers:!1,shaderTextureLOD:!1,clipCullDistance:!1},this.defaultAttributeValues={color:[1,1,1],uv:[0,0],uv1:[0,0]},this.index0AttributeName=void 0,this.uniformsNeedUpdate=!1,this.glslVersion=null,e!==void 0&&this.setValues(e)}copy(e){return super.copy(e),this.fragmentShader=e.fragmentShader,this.vertexShader=e.vertexShader,this.uniforms=Lr(e.uniforms),this.uniformsGroups=px(e.uniformsGroups),this.defines=Object.assign({},e.defines),this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.fog=e.fog,this.lights=e.lights,this.clipping=e.clipping,this.extensions=Object.assign({},e.extensions),this.glslVersion=e.glslVersion,this}toJSON(e){const t=super.toJSON(e);t.glslVersion=this.glslVersion,t.uniforms={};for(const s in this.uniforms){const o=this.uniforms[s].value;o&&o.isTexture?t.uniforms[s]={type:"t",value:o.toJSON(e).uuid}:o&&o.isColor?t.uniforms[s]={type:"c",value:o.getHex()}:o&&o.isVector2?t.uniforms[s]={type:"v2",value:o.toArray()}:o&&o.isVector3?t.uniforms[s]={type:"v3",value:o.toArray()}:o&&o.isVector4?t.uniforms[s]={type:"v4",value:o.toArray()}:o&&o.isMatrix3?t.uniforms[s]={type:"m3",value:o.toArray()}:o&&o.isMatrix4?t.uniforms[s]={type:"m4",value:o.toArray()}:t.uniforms[s]={value:o}}Object.keys(this.defines).length>0&&(t.defines=this.defines),t.vertexShader=this.vertexShader,t.fragmentShader=this.fragmentShader,t.lights=this.lights,t.clipping=this.clipping;const n={};for(const s in this.extensions)this.extensions[s]===!0&&(n[s]=!0);return Object.keys(n).length>0&&(t.extensions=n),t}}class om extends Vt{constructor(){super(),this.isCamera=!0,this.type="Camera",this.matrixWorldInverse=new Lt,this.projectionMatrix=new Lt,this.projectionMatrixInverse=new Lt,this.coordinateSystem=Ri}copy(e,t){return super.copy(e,t),this.matrixWorldInverse.copy(e.matrixWorldInverse),this.projectionMatrix.copy(e.projectionMatrix),this.projectionMatrixInverse.copy(e.projectionMatrixInverse),this.coordinateSystem=e.coordinateSystem,this}getWorldDirection(e){return super.getWorldDirection(e).negate()}updateMatrixWorld(e){super.updateMatrixWorld(e),this.matrixWorldInverse.copy(this.matrixWorld).invert()}updateWorldMatrix(e,t){super.updateWorldMatrix(e,t),this.matrixWorldInverse.copy(this.matrixWorld).invert()}clone(){return new this.constructor().copy(this)}}class Un extends om{constructor(e=50,t=1,n=.1,s=2e3){super(),this.isPerspectiveCamera=!0,this.type="PerspectiveCamera",this.fov=e,this.zoom=1,this.near=n,this.far=s,this.focus=10,this.aspect=t,this.view=null,this.filmGauge=35,this.filmOffset=0,this.updateProjectionMatrix()}copy(e,t){return super.copy(e,t),this.fov=e.fov,this.zoom=e.zoom,this.near=e.near,this.far=e.far,this.focus=e.focus,this.aspect=e.aspect,this.view=e.view===null?null:Object.assign({},e.view),this.filmGauge=e.filmGauge,this.filmOffset=e.filmOffset,this}setFocalLength(e){const t=.5*this.getFilmHeight()/e;this.fov=Hc*2*Math.atan(t),this.updateProjectionMatrix()}getFocalLength(){const e=Math.tan(Aa*.5*this.fov);return .5*this.getFilmHeight()/e}getEffectiveFOV(){return Hc*2*Math.atan(Math.tan(Aa*.5*this.fov)/this.zoom)}getFilmWidth(){return this.filmGauge*Math.min(this.aspect,1)}getFilmHeight(){return this.filmGauge/Math.max(this.aspect,1)}setViewOffset(e,t,n,s,r,o){this.aspect=e/t,this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=e,this.view.fullHeight=t,this.view.offsetX=n,this.view.offsetY=s,this.view.width=r,this.view.height=o,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){const e=this.near;let t=e*Math.tan(Aa*.5*this.fov)/this.zoom,n=2*t,s=this.aspect*n,r=-.5*s;const o=this.view;if(this.view!==null&&this.view.enabled){const l=o.fullWidth,c=o.fullHeight;r+=o.offsetX*s/l,t-=o.offsetY*n/c,s*=o.width/l,n*=o.height/c}const a=this.filmOffset;a!==0&&(r+=e*a/this.getFilmWidth()),this.projectionMatrix.makePerspective(r,r+s,t,t-n,e,this.far,this.coordinateSystem),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(e){const t=super.toJSON(e);return t.object.fov=this.fov,t.object.zoom=this.zoom,t.object.near=this.near,t.object.far=this.far,t.object.focus=this.focus,t.object.aspect=this.aspect,this.view!==null&&(t.object.view=Object.assign({},this.view)),t.object.filmGauge=this.filmGauge,t.object.filmOffset=this.filmOffset,t}}const or=-90,ar=1;class vx extends Vt{constructor(e,t,n){super(),this.type="CubeCamera",this.renderTarget=n,this.coordinateSystem=null,this.activeMipmapLevel=0;const s=new Un(or,ar,e,t);s.layers=this.layers,this.add(s);const r=new Un(or,ar,e,t);r.layers=this.layers,this.add(r);const o=new Un(or,ar,e,t);o.layers=this.layers,this.add(o);const a=new Un(or,ar,e,t);a.layers=this.layers,this.add(a);const l=new Un(or,ar,e,t);l.layers=this.layers,this.add(l);const c=new Un(or,ar,e,t);c.layers=this.layers,this.add(c)}updateCoordinateSystem(){const e=this.coordinateSystem,t=this.children.concat(),[n,s,r,o,a,l]=t;for(const c of t)this.remove(c);if(e===Ri)n.up.set(0,1,0),n.lookAt(1,0,0),s.up.set(0,1,0),s.lookAt(-1,0,0),r.up.set(0,0,-1),r.lookAt(0,1,0),o.up.set(0,0,1),o.lookAt(0,-1,0),a.up.set(0,1,0),a.lookAt(0,0,1),l.up.set(0,1,0),l.lookAt(0,0,-1);else if(e===Xa)n.up.set(0,-1,0),n.lookAt(-1,0,0),s.up.set(0,-1,0),s.lookAt(1,0,0),r.up.set(0,0,1),r.lookAt(0,1,0),o.up.set(0,0,-1),o.lookAt(0,-1,0),a.up.set(0,-1,0),a.lookAt(0,0,1),l.up.set(0,-1,0),l.lookAt(0,0,-1);else throw new Error("THREE.CubeCamera.updateCoordinateSystem(): Invalid coordinate system: "+e);for(const c of t)this.add(c),c.updateMatrixWorld()}update(e,t){this.parent===null&&this.updateMatrixWorld();const{renderTarget:n,activeMipmapLevel:s}=this;this.coordinateSystem!==e.coordinateSystem&&(this.coordinateSystem=e.coordinateSystem,this.updateCoordinateSystem());const[r,o,a,l,c,u]=this.children,f=e.getRenderTarget(),h=e.getActiveCubeFace(),d=e.getActiveMipmapLevel(),g=e.xr.enabled;e.xr.enabled=!1;const _=n.texture.generateMipmaps;n.texture.generateMipmaps=!1,e.setRenderTarget(n,0,s),e.render(t,r),e.setRenderTarget(n,1,s),e.render(t,o),e.setRenderTarget(n,2,s),e.render(t,a),e.setRenderTarget(n,3,s),e.render(t,l),e.setRenderTarget(n,4,s),e.render(t,c),n.texture.generateMipmaps=_,e.setRenderTarget(n,5,s),e.render(t,u),e.setRenderTarget(f,h,d),e.xr.enabled=g,n.texture.needsPMREMUpdate=!0}}class am extends Tn{constructor(e,t,n,s,r,o,a,l,c,u){e=e!==void 0?e:[],t=t!==void 0?t:Rr,super(e,t,n,s,r,o,a,l,c,u),this.isCubeTexture=!0,this.flipY=!1}get images(){return this.image}set images(e){this.image=e}}class xx extends Bs{constructor(e=1,t={}){super(e,e,t),this.isWebGLCubeRenderTarget=!0;const n={width:e,height:e,depth:1},s=[n,n,n,n,n,n];t.encoding!==void 0&&(co("THREE.WebGLCubeRenderTarget: option.encoding has been replaced by option.colorSpace."),t.colorSpace=t.encoding===Us?kt:In),this.texture=new am(s,t.mapping,t.wrapS,t.wrapT,t.magFilter,t.minFilter,t.format,t.type,t.anisotropy,t.colorSpace),this.texture.isRenderTargetTexture=!0,this.texture.generateMipmaps=t.generateMipmaps!==void 0?t.generateMipmaps:!1,this.texture.minFilter=t.minFilter!==void 0?t.minFilter:Dn}fromEquirectangularTexture(e,t){this.texture.type=t.type,this.texture.colorSpace=t.colorSpace,this.texture.generateMipmaps=t.generateMipmaps,this.texture.minFilter=t.minFilter,this.texture.magFilter=t.magFilter;const n={uniforms:{tEquirect:{value:null}},vertexShader:`

				varying vec3 vWorldDirection;

				vec3 transformDirection( in vec3 dir, in mat4 matrix ) {

					return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );

				}

				void main() {

					vWorldDirection = transformDirection( position, modelMatrix );

					#include <begin_vertex>
					#include <project_vertex>

				}
			`,fragmentShader:`

				uniform sampler2D tEquirect;

				varying vec3 vWorldDirection;

				#include <common>

				void main() {

					vec3 direction = normalize( vWorldDirection );

					vec2 sampleUV = equirectUv( direction );

					gl_FragColor = texture2D( tEquirect, sampleUV );

				}
			`},s=new Fo(5,5,5),r=new rs({name:"CubemapFromEquirect",uniforms:Lr(n.uniforms),vertexShader:n.vertexShader,fragmentShader:n.fragmentShader,side:un,blending:Zi});r.uniforms.tEquirect.value=t;const o=new Yi(s,r),a=t.minFilter;return t.minFilter===yo&&(t.minFilter=Dn),new vx(1,10,this).update(e,o),t.minFilter=a,o.geometry.dispose(),o.material.dispose(),this}clear(e,t,n,s){const r=e.getRenderTarget();for(let o=0;o<6;o++)e.setRenderTarget(this,o),e.clear(t,n,s);e.setRenderTarget(r)}}const oc=new $,yx=new $,Sx=new je;class Si{constructor(e=new $(1,0,0),t=0){this.isPlane=!0,this.normal=e,this.constant=t}set(e,t){return this.normal.copy(e),this.constant=t,this}setComponents(e,t,n,s){return this.normal.set(e,t,n),this.constant=s,this}setFromNormalAndCoplanarPoint(e,t){return this.normal.copy(e),this.constant=-t.dot(this.normal),this}setFromCoplanarPoints(e,t,n){const s=oc.subVectors(n,t).cross(yx.subVectors(e,t)).normalize();return this.setFromNormalAndCoplanarPoint(s,e),this}copy(e){return this.normal.copy(e.normal),this.constant=e.constant,this}normalize(){const e=1/this.normal.length();return this.normal.multiplyScalar(e),this.constant*=e,this}negate(){return this.constant*=-1,this.normal.negate(),this}distanceToPoint(e){return this.normal.dot(e)+this.constant}distanceToSphere(e){return this.distanceToPoint(e.center)-e.radius}projectPoint(e,t){return t.copy(e).addScaledVector(this.normal,-this.distanceToPoint(e))}intersectLine(e,t){const n=e.delta(oc),s=this.normal.dot(n);if(s===0)return this.distanceToPoint(e.start)===0?t.copy(e.start):null;const r=-(e.start.dot(this.normal)+this.constant)/s;return r<0||r>1?null:t.copy(e.start).addScaledVector(n,r)}intersectsLine(e){const t=this.distanceToPoint(e.start),n=this.distanceToPoint(e.end);return t<0&&n>0||n<0&&t>0}intersectsBox(e){return e.intersectsPlane(this)}intersectsSphere(e){return e.intersectsPlane(this)}coplanarPoint(e){return e.copy(this.normal).multiplyScalar(-this.constant)}applyMatrix4(e,t){const n=t||Sx.getNormalMatrix(e),s=this.coplanarPoint(oc).applyMatrix4(e),r=this.normal.applyMatrix3(n).normalize();return this.constant=-s.dot(r),this}translate(e){return this.constant-=e.dot(this.normal),this}equals(e){return e.normal.equals(this.normal)&&e.constant===this.constant}clone(){return new this.constructor().copy(this)}}const vs=new _l,fa=new $;class Ru{constructor(e=new Si,t=new Si,n=new Si,s=new Si,r=new Si,o=new Si){this.planes=[e,t,n,s,r,o]}set(e,t,n,s,r,o){const a=this.planes;return a[0].copy(e),a[1].copy(t),a[2].copy(n),a[3].copy(s),a[4].copy(r),a[5].copy(o),this}copy(e){const t=this.planes;for(let n=0;n<6;n++)t[n].copy(e.planes[n]);return this}setFromProjectionMatrix(e,t=Ri){const n=this.planes,s=e.elements,r=s[0],o=s[1],a=s[2],l=s[3],c=s[4],u=s[5],f=s[6],h=s[7],d=s[8],g=s[9],_=s[10],m=s[11],p=s[12],x=s[13],y=s[14],S=s[15];if(n[0].setComponents(l-r,h-c,m-d,S-p).normalize(),n[1].setComponents(l+r,h+c,m+d,S+p).normalize(),n[2].setComponents(l+o,h+u,m+g,S+x).normalize(),n[3].setComponents(l-o,h-u,m-g,S-x).normalize(),n[4].setComponents(l-a,h-f,m-_,S-y).normalize(),t===Ri)n[5].setComponents(l+a,h+f,m+_,S+y).normalize();else if(t===Xa)n[5].setComponents(a,f,_,y).normalize();else throw new Error("THREE.Frustum.setFromProjectionMatrix(): Invalid coordinate system: "+t);return this}intersectsObject(e){if(e.boundingSphere!==void 0)e.boundingSphere===null&&e.computeBoundingSphere(),vs.copy(e.boundingSphere).applyMatrix4(e.matrixWorld);else{const t=e.geometry;t.boundingSphere===null&&t.computeBoundingSphere(),vs.copy(t.boundingSphere).applyMatrix4(e.matrixWorld)}return this.intersectsSphere(vs)}intersectsSprite(e){return vs.center.set(0,0,0),vs.radius=.7071067811865476,vs.applyMatrix4(e.matrixWorld),this.intersectsSphere(vs)}intersectsSphere(e){const t=this.planes,n=e.center,s=-e.radius;for(let r=0;r<6;r++)if(t[r].distanceToPoint(n)<s)return!1;return!0}intersectsBox(e){const t=this.planes;for(let n=0;n<6;n++){const s=t[n];if(fa.x=s.normal.x>0?e.max.x:e.min.x,fa.y=s.normal.y>0?e.max.y:e.min.y,fa.z=s.normal.z>0?e.max.z:e.min.z,s.distanceToPoint(fa)<0)return!1}return!0}containsPoint(e){const t=this.planes;for(let n=0;n<6;n++)if(t[n].distanceToPoint(e)<0)return!1;return!0}clone(){return new this.constructor().copy(this)}}function lm(){let i=null,e=!1,t=null,n=null;function s(r,o){t(r,o),n=i.requestAnimationFrame(s)}return{start:function(){e!==!0&&t!==null&&(n=i.requestAnimationFrame(s),e=!0)},stop:function(){i.cancelAnimationFrame(n),e=!1},setAnimationLoop:function(r){t=r},setContext:function(r){i=r}}}function Mx(i,e){const t=e.isWebGL2,n=new WeakMap;function s(c,u){const f=c.array,h=c.usage,d=f.byteLength,g=i.createBuffer();i.bindBuffer(u,g),i.bufferData(u,f,h),c.onUploadCallback();let _;if(f instanceof Float32Array)_=i.FLOAT;else if(f instanceof Uint16Array)if(c.isFloat16BufferAttribute)if(t)_=i.HALF_FLOAT;else throw new Error("THREE.WebGLAttributes: Usage of Float16BufferAttribute requires WebGL2.");else _=i.UNSIGNED_SHORT;else if(f instanceof Int16Array)_=i.SHORT;else if(f instanceof Uint32Array)_=i.UNSIGNED_INT;else if(f instanceof Int32Array)_=i.INT;else if(f instanceof Int8Array)_=i.BYTE;else if(f instanceof Uint8Array)_=i.UNSIGNED_BYTE;else if(f instanceof Uint8ClampedArray)_=i.UNSIGNED_BYTE;else throw new Error("THREE.WebGLAttributes: Unsupported buffer data format: "+f);return{buffer:g,type:_,bytesPerElement:f.BYTES_PER_ELEMENT,version:c.version,size:d}}function r(c,u,f){const h=u.array,d=u._updateRange,g=u.updateRanges;if(i.bindBuffer(f,c),d.count===-1&&g.length===0&&i.bufferSubData(f,0,h),g.length!==0){for(let _=0,m=g.length;_<m;_++){const p=g[_];t?i.bufferSubData(f,p.start*h.BYTES_PER_ELEMENT,h,p.start,p.count):i.bufferSubData(f,p.start*h.BYTES_PER_ELEMENT,h.subarray(p.start,p.start+p.count))}u.clearUpdateRanges()}d.count!==-1&&(t?i.bufferSubData(f,d.offset*h.BYTES_PER_ELEMENT,h,d.offset,d.count):i.bufferSubData(f,d.offset*h.BYTES_PER_ELEMENT,h.subarray(d.offset,d.offset+d.count)),d.count=-1),u.onUploadCallback()}function o(c){return c.isInterleavedBufferAttribute&&(c=c.data),n.get(c)}function a(c){c.isInterleavedBufferAttribute&&(c=c.data);const u=n.get(c);u&&(i.deleteBuffer(u.buffer),n.delete(c))}function l(c,u){if(c.isGLBufferAttribute){const h=n.get(c);(!h||h.version<c.version)&&n.set(c,{buffer:c.buffer,type:c.type,bytesPerElement:c.elementSize,version:c.version});return}c.isInterleavedBufferAttribute&&(c=c.data);const f=n.get(c);if(f===void 0)n.set(c,s(c,u));else if(f.version<c.version){if(f.size!==c.array.byteLength)throw new Error("THREE.WebGLAttributes: The size of the buffer attribute's array buffer does not match the original size. Resizing buffer attributes is not supported.");r(f.buffer,c,u),f.version=c.version}}return{get:o,remove:a,update:l}}class Cu extends Ni{constructor(e=1,t=1,n=1,s=1){super(),this.type="PlaneGeometry",this.parameters={width:e,height:t,widthSegments:n,heightSegments:s};const r=e/2,o=t/2,a=Math.floor(n),l=Math.floor(s),c=a+1,u=l+1,f=e/a,h=t/l,d=[],g=[],_=[],m=[];for(let p=0;p<u;p++){const x=p*h-o;for(let y=0;y<c;y++){const S=y*f-r;g.push(S,-x,0),_.push(0,0,1),m.push(y/a),m.push(1-p/l)}}for(let p=0;p<l;p++)for(let x=0;x<a;x++){const y=x+c*p,S=x+c*(p+1),R=x+1+c*(p+1),L=x+1+c*p;d.push(y,S,L),d.push(S,R,L)}this.setIndex(d),this.setAttribute("position",new Is(g,3)),this.setAttribute("normal",new Is(_,3)),this.setAttribute("uv",new Is(m,2))}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new Cu(e.width,e.height,e.widthSegments,e.heightSegments)}}var Ex=`#ifdef USE_ALPHAHASH
	if ( diffuseColor.a < getAlphaHashThreshold( vPosition ) ) discard;
#endif`,bx=`#ifdef USE_ALPHAHASH
	const float ALPHA_HASH_SCALE = 0.05;
	float hash2D( vec2 value ) {
		return fract( 1.0e4 * sin( 17.0 * value.x + 0.1 * value.y ) * ( 0.1 + abs( sin( 13.0 * value.y + value.x ) ) ) );
	}
	float hash3D( vec3 value ) {
		return hash2D( vec2( hash2D( value.xy ), value.z ) );
	}
	float getAlphaHashThreshold( vec3 position ) {
		float maxDeriv = max(
			length( dFdx( position.xyz ) ),
			length( dFdy( position.xyz ) )
		);
		float pixScale = 1.0 / ( ALPHA_HASH_SCALE * maxDeriv );
		vec2 pixScales = vec2(
			exp2( floor( log2( pixScale ) ) ),
			exp2( ceil( log2( pixScale ) ) )
		);
		vec2 alpha = vec2(
			hash3D( floor( pixScales.x * position.xyz ) ),
			hash3D( floor( pixScales.y * position.xyz ) )
		);
		float lerpFactor = fract( log2( pixScale ) );
		float x = ( 1.0 - lerpFactor ) * alpha.x + lerpFactor * alpha.y;
		float a = min( lerpFactor, 1.0 - lerpFactor );
		vec3 cases = vec3(
			x * x / ( 2.0 * a * ( 1.0 - a ) ),
			( x - 0.5 * a ) / ( 1.0 - a ),
			1.0 - ( ( 1.0 - x ) * ( 1.0 - x ) / ( 2.0 * a * ( 1.0 - a ) ) )
		);
		float threshold = ( x < ( 1.0 - a ) )
			? ( ( x < a ) ? cases.x : cases.y )
			: cases.z;
		return clamp( threshold , 1.0e-6, 1.0 );
	}
#endif`,Tx=`#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, vAlphaMapUv ).g;
#endif`,Ax=`#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,wx=`#ifdef USE_ALPHATEST
	if ( diffuseColor.a < alphaTest ) discard;
#endif`,Rx=`#ifdef USE_ALPHATEST
	uniform float alphaTest;
#endif`,Cx=`#ifdef USE_AOMAP
	float ambientOcclusion = ( texture2D( aoMap, vAoMapUv ).r - 1.0 ) * aoMapIntensity + 1.0;
	reflectedLight.indirectDiffuse *= ambientOcclusion;
	#if defined( USE_CLEARCOAT ) 
		clearcoatSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_SHEEN ) 
		sheenSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD )
		float dotNV = saturate( dot( geometryNormal, geometryViewDir ) );
		reflectedLight.indirectSpecular *= computeSpecularOcclusion( dotNV, ambientOcclusion, material.roughness );
	#endif
#endif`,Px=`#ifdef USE_AOMAP
	uniform sampler2D aoMap;
	uniform float aoMapIntensity;
#endif`,Lx=`#ifdef USE_BATCHING
	attribute float batchId;
	uniform highp sampler2D batchingTexture;
	mat4 getBatchingMatrix( const in float i ) {
		int size = textureSize( batchingTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( batchingTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( batchingTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( batchingTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( batchingTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
#endif`,Dx=`#ifdef USE_BATCHING
	mat4 batchingMatrix = getBatchingMatrix( batchId );
#endif`,Ux=`vec3 transformed = vec3( position );
#ifdef USE_ALPHAHASH
	vPosition = vec3( position );
#endif`,Ix=`vec3 objectNormal = vec3( normal );
#ifdef USE_TANGENT
	vec3 objectTangent = vec3( tangent.xyz );
#endif`,Ox=`float G_BlinnPhong_Implicit( ) {
	return 0.25;
}
float D_BlinnPhong( const in float shininess, const in float dotNH ) {
	return RECIPROCAL_PI * ( shininess * 0.5 + 1.0 ) * pow( dotNH, shininess );
}
vec3 BRDF_BlinnPhong( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in vec3 specularColor, const in float shininess ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( specularColor, 1.0, dotVH );
	float G = G_BlinnPhong_Implicit( );
	float D = D_BlinnPhong( shininess, dotNH );
	return F * ( G * D );
} // validated`,Nx=`#ifdef USE_IRIDESCENCE
	const mat3 XYZ_TO_REC709 = mat3(
		 3.2404542, -0.9692660,  0.0556434,
		-1.5371385,  1.8760108, -0.2040259,
		-0.4985314,  0.0415560,  1.0572252
	);
	vec3 Fresnel0ToIor( vec3 fresnel0 ) {
		vec3 sqrtF0 = sqrt( fresnel0 );
		return ( vec3( 1.0 ) + sqrtF0 ) / ( vec3( 1.0 ) - sqrtF0 );
	}
	vec3 IorToFresnel0( vec3 transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - vec3( incidentIor ) ) / ( transmittedIor + vec3( incidentIor ) ) );
	}
	float IorToFresnel0( float transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - incidentIor ) / ( transmittedIor + incidentIor ));
	}
	vec3 evalSensitivity( float OPD, vec3 shift ) {
		float phase = 2.0 * PI * OPD * 1.0e-9;
		vec3 val = vec3( 5.4856e-13, 4.4201e-13, 5.2481e-13 );
		vec3 pos = vec3( 1.6810e+06, 1.7953e+06, 2.2084e+06 );
		vec3 var = vec3( 4.3278e+09, 9.3046e+09, 6.6121e+09 );
		vec3 xyz = val * sqrt( 2.0 * PI * var ) * cos( pos * phase + shift ) * exp( - pow2( phase ) * var );
		xyz.x += 9.7470e-14 * sqrt( 2.0 * PI * 4.5282e+09 ) * cos( 2.2399e+06 * phase + shift[ 0 ] ) * exp( - 4.5282e+09 * pow2( phase ) );
		xyz /= 1.0685e-7;
		vec3 rgb = XYZ_TO_REC709 * xyz;
		return rgb;
	}
	vec3 evalIridescence( float outsideIOR, float eta2, float cosTheta1, float thinFilmThickness, vec3 baseF0 ) {
		vec3 I;
		float iridescenceIOR = mix( outsideIOR, eta2, smoothstep( 0.0, 0.03, thinFilmThickness ) );
		float sinTheta2Sq = pow2( outsideIOR / iridescenceIOR ) * ( 1.0 - pow2( cosTheta1 ) );
		float cosTheta2Sq = 1.0 - sinTheta2Sq;
		if ( cosTheta2Sq < 0.0 ) {
			return vec3( 1.0 );
		}
		float cosTheta2 = sqrt( cosTheta2Sq );
		float R0 = IorToFresnel0( iridescenceIOR, outsideIOR );
		float R12 = F_Schlick( R0, 1.0, cosTheta1 );
		float T121 = 1.0 - R12;
		float phi12 = 0.0;
		if ( iridescenceIOR < outsideIOR ) phi12 = PI;
		float phi21 = PI - phi12;
		vec3 baseIOR = Fresnel0ToIor( clamp( baseF0, 0.0, 0.9999 ) );		vec3 R1 = IorToFresnel0( baseIOR, iridescenceIOR );
		vec3 R23 = F_Schlick( R1, 1.0, cosTheta2 );
		vec3 phi23 = vec3( 0.0 );
		if ( baseIOR[ 0 ] < iridescenceIOR ) phi23[ 0 ] = PI;
		if ( baseIOR[ 1 ] < iridescenceIOR ) phi23[ 1 ] = PI;
		if ( baseIOR[ 2 ] < iridescenceIOR ) phi23[ 2 ] = PI;
		float OPD = 2.0 * iridescenceIOR * thinFilmThickness * cosTheta2;
		vec3 phi = vec3( phi21 ) + phi23;
		vec3 R123 = clamp( R12 * R23, 1e-5, 0.9999 );
		vec3 r123 = sqrt( R123 );
		vec3 Rs = pow2( T121 ) * R23 / ( vec3( 1.0 ) - R123 );
		vec3 C0 = R12 + Rs;
		I = C0;
		vec3 Cm = Rs - T121;
		for ( int m = 1; m <= 2; ++ m ) {
			Cm *= r123;
			vec3 Sm = 2.0 * evalSensitivity( float( m ) * OPD, float( m ) * phi );
			I += Cm * Sm;
		}
		return max( I, vec3( 0.0 ) );
	}
#endif`,Fx=`#ifdef USE_BUMPMAP
	uniform sampler2D bumpMap;
	uniform float bumpScale;
	vec2 dHdxy_fwd() {
		vec2 dSTdx = dFdx( vBumpMapUv );
		vec2 dSTdy = dFdy( vBumpMapUv );
		float Hll = bumpScale * texture2D( bumpMap, vBumpMapUv ).x;
		float dBx = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdx ).x - Hll;
		float dBy = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdy ).x - Hll;
		return vec2( dBx, dBy );
	}
	vec3 perturbNormalArb( vec3 surf_pos, vec3 surf_norm, vec2 dHdxy, float faceDirection ) {
		vec3 vSigmaX = normalize( dFdx( surf_pos.xyz ) );
		vec3 vSigmaY = normalize( dFdy( surf_pos.xyz ) );
		vec3 vN = surf_norm;
		vec3 R1 = cross( vSigmaY, vN );
		vec3 R2 = cross( vN, vSigmaX );
		float fDet = dot( vSigmaX, R1 ) * faceDirection;
		vec3 vGrad = sign( fDet ) * ( dHdxy.x * R1 + dHdxy.y * R2 );
		return normalize( abs( fDet ) * surf_norm - vGrad );
	}
#endif`,zx=`#if NUM_CLIPPING_PLANES > 0
	vec4 plane;
	#pragma unroll_loop_start
	for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
		plane = clippingPlanes[ i ];
		if ( dot( vClipPosition, plane.xyz ) > plane.w ) discard;
	}
	#pragma unroll_loop_end
	#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
		bool clipped = true;
		#pragma unroll_loop_start
		for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			clipped = ( dot( vClipPosition, plane.xyz ) > plane.w ) && clipped;
		}
		#pragma unroll_loop_end
		if ( clipped ) discard;
	#endif
#endif`,Bx=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
	uniform vec4 clippingPlanes[ NUM_CLIPPING_PLANES ];
#endif`,kx=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
#endif`,Vx=`#if NUM_CLIPPING_PLANES > 0
	vClipPosition = - mvPosition.xyz;
#endif`,Hx=`#if defined( USE_COLOR_ALPHA )
	diffuseColor *= vColor;
#elif defined( USE_COLOR )
	diffuseColor.rgb *= vColor;
#endif`,Gx=`#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR )
	varying vec3 vColor;
#endif`,Wx=`#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR )
	varying vec3 vColor;
#endif`,Xx=`#if defined( USE_COLOR_ALPHA )
	vColor = vec4( 1.0 );
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR )
	vColor = vec3( 1.0 );
#endif
#ifdef USE_COLOR
	vColor *= color;
#endif
#ifdef USE_INSTANCING_COLOR
	vColor.xyz *= instanceColor.xyz;
#endif`,qx=`#define PI 3.141592653589793
#define PI2 6.283185307179586
#define PI_HALF 1.5707963267948966
#define RECIPROCAL_PI 0.3183098861837907
#define RECIPROCAL_PI2 0.15915494309189535
#define EPSILON 1e-6
#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
#define whiteComplement( a ) ( 1.0 - saturate( a ) )
float pow2( const in float x ) { return x*x; }
vec3 pow2( const in vec3 x ) { return x*x; }
float pow3( const in float x ) { return x*x*x; }
float pow4( const in float x ) { float x2 = x*x; return x2*x2; }
float max3( const in vec3 v ) { return max( max( v.x, v.y ), v.z ); }
float average( const in vec3 v ) { return dot( v, vec3( 0.3333333 ) ); }
highp float rand( const in vec2 uv ) {
	const highp float a = 12.9898, b = 78.233, c = 43758.5453;
	highp float dt = dot( uv.xy, vec2( a,b ) ), sn = mod( dt, PI );
	return fract( sin( sn ) * c );
}
#ifdef HIGH_PRECISION
	float precisionSafeLength( vec3 v ) { return length( v ); }
#else
	float precisionSafeLength( vec3 v ) {
		float maxComponent = max3( abs( v ) );
		return length( v / maxComponent ) * maxComponent;
	}
#endif
struct IncidentLight {
	vec3 color;
	vec3 direction;
	bool visible;
};
struct ReflectedLight {
	vec3 directDiffuse;
	vec3 directSpecular;
	vec3 indirectDiffuse;
	vec3 indirectSpecular;
};
#ifdef USE_ALPHAHASH
	varying vec3 vPosition;
#endif
vec3 transformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );
}
vec3 inverseTransformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( vec4( dir, 0.0 ) * matrix ).xyz );
}
mat3 transposeMat3( const in mat3 m ) {
	mat3 tmp;
	tmp[ 0 ] = vec3( m[ 0 ].x, m[ 1 ].x, m[ 2 ].x );
	tmp[ 1 ] = vec3( m[ 0 ].y, m[ 1 ].y, m[ 2 ].y );
	tmp[ 2 ] = vec3( m[ 0 ].z, m[ 1 ].z, m[ 2 ].z );
	return tmp;
}
float luminance( const in vec3 rgb ) {
	const vec3 weights = vec3( 0.2126729, 0.7151522, 0.0721750 );
	return dot( weights, rgb );
}
bool isPerspectiveMatrix( mat4 m ) {
	return m[ 2 ][ 3 ] == - 1.0;
}
vec2 equirectUv( in vec3 dir ) {
	float u = atan( dir.z, dir.x ) * RECIPROCAL_PI2 + 0.5;
	float v = asin( clamp( dir.y, - 1.0, 1.0 ) ) * RECIPROCAL_PI + 0.5;
	return vec2( u, v );
}
vec3 BRDF_Lambert( const in vec3 diffuseColor ) {
	return RECIPROCAL_PI * diffuseColor;
}
vec3 F_Schlick( const in vec3 f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
}
float F_Schlick( const in float f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
} // validated`,Yx=`#ifdef ENVMAP_TYPE_CUBE_UV
	#define cubeUV_minMipLevel 4.0
	#define cubeUV_minTileSize 16.0
	float getFace( vec3 direction ) {
		vec3 absDirection = abs( direction );
		float face = - 1.0;
		if ( absDirection.x > absDirection.z ) {
			if ( absDirection.x > absDirection.y )
				face = direction.x > 0.0 ? 0.0 : 3.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		} else {
			if ( absDirection.z > absDirection.y )
				face = direction.z > 0.0 ? 2.0 : 5.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		}
		return face;
	}
	vec2 getUV( vec3 direction, float face ) {
		vec2 uv;
		if ( face == 0.0 ) {
			uv = vec2( direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 1.0 ) {
			uv = vec2( - direction.x, - direction.z ) / abs( direction.y );
		} else if ( face == 2.0 ) {
			uv = vec2( - direction.x, direction.y ) / abs( direction.z );
		} else if ( face == 3.0 ) {
			uv = vec2( - direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 4.0 ) {
			uv = vec2( - direction.x, direction.z ) / abs( direction.y );
		} else {
			uv = vec2( direction.x, direction.y ) / abs( direction.z );
		}
		return 0.5 * ( uv + 1.0 );
	}
	vec3 bilinearCubeUV( sampler2D envMap, vec3 direction, float mipInt ) {
		float face = getFace( direction );
		float filterInt = max( cubeUV_minMipLevel - mipInt, 0.0 );
		mipInt = max( mipInt, cubeUV_minMipLevel );
		float faceSize = exp2( mipInt );
		highp vec2 uv = getUV( direction, face ) * ( faceSize - 2.0 ) + 1.0;
		if ( face > 2.0 ) {
			uv.y += faceSize;
			face -= 3.0;
		}
		uv.x += face * faceSize;
		uv.x += filterInt * 3.0 * cubeUV_minTileSize;
		uv.y += 4.0 * ( exp2( CUBEUV_MAX_MIP ) - faceSize );
		uv.x *= CUBEUV_TEXEL_WIDTH;
		uv.y *= CUBEUV_TEXEL_HEIGHT;
		#ifdef texture2DGradEXT
			return texture2DGradEXT( envMap, uv, vec2( 0.0 ), vec2( 0.0 ) ).rgb;
		#else
			return texture2D( envMap, uv ).rgb;
		#endif
	}
	#define cubeUV_r0 1.0
	#define cubeUV_m0 - 2.0
	#define cubeUV_r1 0.8
	#define cubeUV_m1 - 1.0
	#define cubeUV_r4 0.4
	#define cubeUV_m4 2.0
	#define cubeUV_r5 0.305
	#define cubeUV_m5 3.0
	#define cubeUV_r6 0.21
	#define cubeUV_m6 4.0
	float roughnessToMip( float roughness ) {
		float mip = 0.0;
		if ( roughness >= cubeUV_r1 ) {
			mip = ( cubeUV_r0 - roughness ) * ( cubeUV_m1 - cubeUV_m0 ) / ( cubeUV_r0 - cubeUV_r1 ) + cubeUV_m0;
		} else if ( roughness >= cubeUV_r4 ) {
			mip = ( cubeUV_r1 - roughness ) * ( cubeUV_m4 - cubeUV_m1 ) / ( cubeUV_r1 - cubeUV_r4 ) + cubeUV_m1;
		} else if ( roughness >= cubeUV_r5 ) {
			mip = ( cubeUV_r4 - roughness ) * ( cubeUV_m5 - cubeUV_m4 ) / ( cubeUV_r4 - cubeUV_r5 ) + cubeUV_m4;
		} else if ( roughness >= cubeUV_r6 ) {
			mip = ( cubeUV_r5 - roughness ) * ( cubeUV_m6 - cubeUV_m5 ) / ( cubeUV_r5 - cubeUV_r6 ) + cubeUV_m5;
		} else {
			mip = - 2.0 * log2( 1.16 * roughness );		}
		return mip;
	}
	vec4 textureCubeUV( sampler2D envMap, vec3 sampleDir, float roughness ) {
		float mip = clamp( roughnessToMip( roughness ), cubeUV_m0, CUBEUV_MAX_MIP );
		float mipF = fract( mip );
		float mipInt = floor( mip );
		vec3 color0 = bilinearCubeUV( envMap, sampleDir, mipInt );
		if ( mipF == 0.0 ) {
			return vec4( color0, 1.0 );
		} else {
			vec3 color1 = bilinearCubeUV( envMap, sampleDir, mipInt + 1.0 );
			return vec4( mix( color0, color1, mipF ), 1.0 );
		}
	}
#endif`,$x=`vec3 transformedNormal = objectNormal;
#ifdef USE_TANGENT
	vec3 transformedTangent = objectTangent;
#endif
#ifdef USE_BATCHING
	mat3 bm = mat3( batchingMatrix );
	transformedNormal /= vec3( dot( bm[ 0 ], bm[ 0 ] ), dot( bm[ 1 ], bm[ 1 ] ), dot( bm[ 2 ], bm[ 2 ] ) );
	transformedNormal = bm * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = bm * transformedTangent;
	#endif
#endif
#ifdef USE_INSTANCING
	mat3 im = mat3( instanceMatrix );
	transformedNormal /= vec3( dot( im[ 0 ], im[ 0 ] ), dot( im[ 1 ], im[ 1 ] ), dot( im[ 2 ], im[ 2 ] ) );
	transformedNormal = im * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = im * transformedTangent;
	#endif
#endif
transformedNormal = normalMatrix * transformedNormal;
#ifdef FLIP_SIDED
	transformedNormal = - transformedNormal;
#endif
#ifdef USE_TANGENT
	transformedTangent = ( modelViewMatrix * vec4( transformedTangent, 0.0 ) ).xyz;
	#ifdef FLIP_SIDED
		transformedTangent = - transformedTangent;
	#endif
#endif`,jx=`#ifdef USE_DISPLACEMENTMAP
	uniform sampler2D displacementMap;
	uniform float displacementScale;
	uniform float displacementBias;
#endif`,Kx=`#ifdef USE_DISPLACEMENTMAP
	transformed += normalize( objectNormal ) * ( texture2D( displacementMap, vDisplacementMapUv ).x * displacementScale + displacementBias );
#endif`,Zx=`#ifdef USE_EMISSIVEMAP
	vec4 emissiveColor = texture2D( emissiveMap, vEmissiveMapUv );
	totalEmissiveRadiance *= emissiveColor.rgb;
#endif`,Jx=`#ifdef USE_EMISSIVEMAP
	uniform sampler2D emissiveMap;
#endif`,Qx="gl_FragColor = linearToOutputTexel( gl_FragColor );",ey=`
const mat3 LINEAR_SRGB_TO_LINEAR_DISPLAY_P3 = mat3(
	vec3( 0.8224621, 0.177538, 0.0 ),
	vec3( 0.0331941, 0.9668058, 0.0 ),
	vec3( 0.0170827, 0.0723974, 0.9105199 )
);
const mat3 LINEAR_DISPLAY_P3_TO_LINEAR_SRGB = mat3(
	vec3( 1.2249401, - 0.2249404, 0.0 ),
	vec3( - 0.0420569, 1.0420571, 0.0 ),
	vec3( - 0.0196376, - 0.0786361, 1.0982735 )
);
vec4 LinearSRGBToLinearDisplayP3( in vec4 value ) {
	return vec4( value.rgb * LINEAR_SRGB_TO_LINEAR_DISPLAY_P3, value.a );
}
vec4 LinearDisplayP3ToLinearSRGB( in vec4 value ) {
	return vec4( value.rgb * LINEAR_DISPLAY_P3_TO_LINEAR_SRGB, value.a );
}
vec4 LinearTransferOETF( in vec4 value ) {
	return value;
}
vec4 sRGBTransferOETF( in vec4 value ) {
	return vec4( mix( pow( value.rgb, vec3( 0.41666 ) ) * 1.055 - vec3( 0.055 ), value.rgb * 12.92, vec3( lessThanEqual( value.rgb, vec3( 0.0031308 ) ) ) ), value.a );
}
vec4 LinearToLinear( in vec4 value ) {
	return value;
}
vec4 LinearTosRGB( in vec4 value ) {
	return sRGBTransferOETF( value );
}`,ty=`#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vec3 cameraToFrag;
		if ( isOrthographic ) {
			cameraToFrag = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToFrag = normalize( vWorldPosition - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vec3 reflectVec = reflect( cameraToFrag, worldNormal );
		#else
			vec3 reflectVec = refract( cameraToFrag, worldNormal, refractionRatio );
		#endif
	#else
		vec3 reflectVec = vReflect;
	#endif
	#ifdef ENVMAP_TYPE_CUBE
		vec4 envColor = textureCube( envMap, vec3( flipEnvMap * reflectVec.x, reflectVec.yz ) );
	#else
		vec4 envColor = vec4( 0.0 );
	#endif
	#ifdef ENVMAP_BLENDING_MULTIPLY
		outgoingLight = mix( outgoingLight, outgoingLight * envColor.xyz, specularStrength * reflectivity );
	#elif defined( ENVMAP_BLENDING_MIX )
		outgoingLight = mix( outgoingLight, envColor.xyz, specularStrength * reflectivity );
	#elif defined( ENVMAP_BLENDING_ADD )
		outgoingLight += envColor.xyz * specularStrength * reflectivity;
	#endif
#endif`,ny=`#ifdef USE_ENVMAP
	uniform float envMapIntensity;
	uniform float flipEnvMap;
	#ifdef ENVMAP_TYPE_CUBE
		uniform samplerCube envMap;
	#else
		uniform sampler2D envMap;
	#endif
	
#endif`,iy=`#ifdef USE_ENVMAP
	uniform float reflectivity;
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		varying vec3 vWorldPosition;
		uniform float refractionRatio;
	#else
		varying vec3 vReflect;
	#endif
#endif`,sy=`#ifdef USE_ENVMAP
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		
		varying vec3 vWorldPosition;
	#else
		varying vec3 vReflect;
		uniform float refractionRatio;
	#endif
#endif`,ry=`#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vWorldPosition = worldPosition.xyz;
	#else
		vec3 cameraToVertex;
		if ( isOrthographic ) {
			cameraToVertex = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToVertex = normalize( worldPosition.xyz - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vReflect = reflect( cameraToVertex, worldNormal );
		#else
			vReflect = refract( cameraToVertex, worldNormal, refractionRatio );
		#endif
	#endif
#endif`,oy=`#ifdef USE_FOG
	vFogDepth = - mvPosition.z;
#endif`,ay=`#ifdef USE_FOG
	varying float vFogDepth;
#endif`,ly=`#ifdef USE_FOG
	#ifdef FOG_EXP2
		float fogFactor = 1.0 - exp( - fogDensity * fogDensity * vFogDepth * vFogDepth );
	#else
		float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
	#endif
	gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );
#endif`,cy=`#ifdef USE_FOG
	uniform vec3 fogColor;
	varying float vFogDepth;
	#ifdef FOG_EXP2
		uniform float fogDensity;
	#else
		uniform float fogNear;
		uniform float fogFar;
	#endif
#endif`,uy=`#ifdef USE_GRADIENTMAP
	uniform sampler2D gradientMap;
#endif
vec3 getGradientIrradiance( vec3 normal, vec3 lightDirection ) {
	float dotNL = dot( normal, lightDirection );
	vec2 coord = vec2( dotNL * 0.5 + 0.5, 0.0 );
	#ifdef USE_GRADIENTMAP
		return vec3( texture2D( gradientMap, coord ).r );
	#else
		vec2 fw = fwidth( coord ) * 0.5;
		return mix( vec3( 0.7 ), vec3( 1.0 ), smoothstep( 0.7 - fw.x, 0.7 + fw.x, coord.x ) );
	#endif
}`,fy=`#ifdef USE_LIGHTMAP
	vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
	vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapIntensity;
	reflectedLight.indirectDiffuse += lightMapIrradiance;
#endif`,hy=`#ifdef USE_LIGHTMAP
	uniform sampler2D lightMap;
	uniform float lightMapIntensity;
#endif`,dy=`LambertMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularStrength = specularStrength;`,py=`varying vec3 vViewPosition;
struct LambertMaterial {
	vec3 diffuseColor;
	float specularStrength;
};
void RE_Direct_Lambert( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Lambert( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Lambert
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Lambert`,my=`uniform bool receiveShadow;
uniform vec3 ambientLightColor;
#if defined( USE_LIGHT_PROBES )
	uniform vec3 lightProbe[ 9 ];
#endif
vec3 shGetIrradianceAt( in vec3 normal, in vec3 shCoefficients[ 9 ] ) {
	float x = normal.x, y = normal.y, z = normal.z;
	vec3 result = shCoefficients[ 0 ] * 0.886227;
	result += shCoefficients[ 1 ] * 2.0 * 0.511664 * y;
	result += shCoefficients[ 2 ] * 2.0 * 0.511664 * z;
	result += shCoefficients[ 3 ] * 2.0 * 0.511664 * x;
	result += shCoefficients[ 4 ] * 2.0 * 0.429043 * x * y;
	result += shCoefficients[ 5 ] * 2.0 * 0.429043 * y * z;
	result += shCoefficients[ 6 ] * ( 0.743125 * z * z - 0.247708 );
	result += shCoefficients[ 7 ] * 2.0 * 0.429043 * x * z;
	result += shCoefficients[ 8 ] * 0.429043 * ( x * x - y * y );
	return result;
}
vec3 getLightProbeIrradiance( const in vec3 lightProbe[ 9 ], const in vec3 normal ) {
	vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
	vec3 irradiance = shGetIrradianceAt( worldNormal, lightProbe );
	return irradiance;
}
vec3 getAmbientLightIrradiance( const in vec3 ambientLightColor ) {
	vec3 irradiance = ambientLightColor;
	return irradiance;
}
float getDistanceAttenuation( const in float lightDistance, const in float cutoffDistance, const in float decayExponent ) {
	#if defined ( LEGACY_LIGHTS )
		if ( cutoffDistance > 0.0 && decayExponent > 0.0 ) {
			return pow( saturate( - lightDistance / cutoffDistance + 1.0 ), decayExponent );
		}
		return 1.0;
	#else
		float distanceFalloff = 1.0 / max( pow( lightDistance, decayExponent ), 0.01 );
		if ( cutoffDistance > 0.0 ) {
			distanceFalloff *= pow2( saturate( 1.0 - pow4( lightDistance / cutoffDistance ) ) );
		}
		return distanceFalloff;
	#endif
}
float getSpotAttenuation( const in float coneCosine, const in float penumbraCosine, const in float angleCosine ) {
	return smoothstep( coneCosine, penumbraCosine, angleCosine );
}
#if NUM_DIR_LIGHTS > 0
	struct DirectionalLight {
		vec3 direction;
		vec3 color;
	};
	uniform DirectionalLight directionalLights[ NUM_DIR_LIGHTS ];
	void getDirectionalLightInfo( const in DirectionalLight directionalLight, out IncidentLight light ) {
		light.color = directionalLight.color;
		light.direction = directionalLight.direction;
		light.visible = true;
	}
#endif
#if NUM_POINT_LIGHTS > 0
	struct PointLight {
		vec3 position;
		vec3 color;
		float distance;
		float decay;
	};
	uniform PointLight pointLights[ NUM_POINT_LIGHTS ];
	void getPointLightInfo( const in PointLight pointLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = pointLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float lightDistance = length( lVector );
		light.color = pointLight.color;
		light.color *= getDistanceAttenuation( lightDistance, pointLight.distance, pointLight.decay );
		light.visible = ( light.color != vec3( 0.0 ) );
	}
#endif
#if NUM_SPOT_LIGHTS > 0
	struct SpotLight {
		vec3 position;
		vec3 direction;
		vec3 color;
		float distance;
		float decay;
		float coneCos;
		float penumbraCos;
	};
	uniform SpotLight spotLights[ NUM_SPOT_LIGHTS ];
	void getSpotLightInfo( const in SpotLight spotLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = spotLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float angleCos = dot( light.direction, spotLight.direction );
		float spotAttenuation = getSpotAttenuation( spotLight.coneCos, spotLight.penumbraCos, angleCos );
		if ( spotAttenuation > 0.0 ) {
			float lightDistance = length( lVector );
			light.color = spotLight.color * spotAttenuation;
			light.color *= getDistanceAttenuation( lightDistance, spotLight.distance, spotLight.decay );
			light.visible = ( light.color != vec3( 0.0 ) );
		} else {
			light.color = vec3( 0.0 );
			light.visible = false;
		}
	}
#endif
#if NUM_RECT_AREA_LIGHTS > 0
	struct RectAreaLight {
		vec3 color;
		vec3 position;
		vec3 halfWidth;
		vec3 halfHeight;
	};
	uniform sampler2D ltc_1;	uniform sampler2D ltc_2;
	uniform RectAreaLight rectAreaLights[ NUM_RECT_AREA_LIGHTS ];
#endif
#if NUM_HEMI_LIGHTS > 0
	struct HemisphereLight {
		vec3 direction;
		vec3 skyColor;
		vec3 groundColor;
	};
	uniform HemisphereLight hemisphereLights[ NUM_HEMI_LIGHTS ];
	vec3 getHemisphereLightIrradiance( const in HemisphereLight hemiLight, const in vec3 normal ) {
		float dotNL = dot( normal, hemiLight.direction );
		float hemiDiffuseWeight = 0.5 * dotNL + 0.5;
		vec3 irradiance = mix( hemiLight.groundColor, hemiLight.skyColor, hemiDiffuseWeight );
		return irradiance;
	}
#endif`,_y=`#ifdef USE_ENVMAP
	vec3 getIBLIrradiance( const in vec3 normal ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, worldNormal, 1.0 );
			return PI * envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	vec3 getIBLRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 reflectVec = reflect( - viewDir, normal );
			reflectVec = normalize( mix( reflectVec, normal, roughness * roughness) );
			reflectVec = inverseTransformDirection( reflectVec, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, reflectVec, roughness );
			return envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	#ifdef USE_ANISOTROPY
		vec3 getIBLAnisotropyRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness, const in vec3 bitangent, const in float anisotropy ) {
			#ifdef ENVMAP_TYPE_CUBE_UV
				vec3 bentNormal = cross( bitangent, viewDir );
				bentNormal = normalize( cross( bentNormal, bitangent ) );
				bentNormal = normalize( mix( bentNormal, normal, pow2( pow2( 1.0 - anisotropy * ( 1.0 - roughness ) ) ) ) );
				return getIBLRadiance( viewDir, bentNormal, roughness );
			#else
				return vec3( 0.0 );
			#endif
		}
	#endif
#endif`,gy=`ToonMaterial material;
material.diffuseColor = diffuseColor.rgb;`,vy=`varying vec3 vViewPosition;
struct ToonMaterial {
	vec3 diffuseColor;
};
void RE_Direct_Toon( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	vec3 irradiance = getGradientIrradiance( geometryNormal, directLight.direction ) * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Toon( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Toon
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Toon`,xy=`BlinnPhongMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularColor = specular;
material.specularShininess = shininess;
material.specularStrength = specularStrength;`,yy=`varying vec3 vViewPosition;
struct BlinnPhongMaterial {
	vec3 diffuseColor;
	vec3 specularColor;
	float specularShininess;
	float specularStrength;
};
void RE_Direct_BlinnPhong( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
	reflectedLight.directSpecular += irradiance * BRDF_BlinnPhong( directLight.direction, geometryViewDir, geometryNormal, material.specularColor, material.specularShininess ) * material.specularStrength;
}
void RE_IndirectDiffuse_BlinnPhong( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_BlinnPhong
#define RE_IndirectDiffuse		RE_IndirectDiffuse_BlinnPhong`,Sy=`PhysicalMaterial material;
material.diffuseColor = diffuseColor.rgb * ( 1.0 - metalnessFactor );
vec3 dxy = max( abs( dFdx( nonPerturbedNormal ) ), abs( dFdy( nonPerturbedNormal ) ) );
float geometryRoughness = max( max( dxy.x, dxy.y ), dxy.z );
material.roughness = max( roughnessFactor, 0.0525 );material.roughness += geometryRoughness;
material.roughness = min( material.roughness, 1.0 );
#ifdef IOR
	material.ior = ior;
	#ifdef USE_SPECULAR
		float specularIntensityFactor = specularIntensity;
		vec3 specularColorFactor = specularColor;
		#ifdef USE_SPECULAR_COLORMAP
			specularColorFactor *= texture2D( specularColorMap, vSpecularColorMapUv ).rgb;
		#endif
		#ifdef USE_SPECULAR_INTENSITYMAP
			specularIntensityFactor *= texture2D( specularIntensityMap, vSpecularIntensityMapUv ).a;
		#endif
		material.specularF90 = mix( specularIntensityFactor, 1.0, metalnessFactor );
	#else
		float specularIntensityFactor = 1.0;
		vec3 specularColorFactor = vec3( 1.0 );
		material.specularF90 = 1.0;
	#endif
	material.specularColor = mix( min( pow2( ( material.ior - 1.0 ) / ( material.ior + 1.0 ) ) * specularColorFactor, vec3( 1.0 ) ) * specularIntensityFactor, diffuseColor.rgb, metalnessFactor );
#else
	material.specularColor = mix( vec3( 0.04 ), diffuseColor.rgb, metalnessFactor );
	material.specularF90 = 1.0;
#endif
#ifdef USE_CLEARCOAT
	material.clearcoat = clearcoat;
	material.clearcoatRoughness = clearcoatRoughness;
	material.clearcoatF0 = vec3( 0.04 );
	material.clearcoatF90 = 1.0;
	#ifdef USE_CLEARCOATMAP
		material.clearcoat *= texture2D( clearcoatMap, vClearcoatMapUv ).x;
	#endif
	#ifdef USE_CLEARCOAT_ROUGHNESSMAP
		material.clearcoatRoughness *= texture2D( clearcoatRoughnessMap, vClearcoatRoughnessMapUv ).y;
	#endif
	material.clearcoat = saturate( material.clearcoat );	material.clearcoatRoughness = max( material.clearcoatRoughness, 0.0525 );
	material.clearcoatRoughness += geometryRoughness;
	material.clearcoatRoughness = min( material.clearcoatRoughness, 1.0 );
#endif
#ifdef USE_IRIDESCENCE
	material.iridescence = iridescence;
	material.iridescenceIOR = iridescenceIOR;
	#ifdef USE_IRIDESCENCEMAP
		material.iridescence *= texture2D( iridescenceMap, vIridescenceMapUv ).r;
	#endif
	#ifdef USE_IRIDESCENCE_THICKNESSMAP
		material.iridescenceThickness = (iridescenceThicknessMaximum - iridescenceThicknessMinimum) * texture2D( iridescenceThicknessMap, vIridescenceThicknessMapUv ).g + iridescenceThicknessMinimum;
	#else
		material.iridescenceThickness = iridescenceThicknessMaximum;
	#endif
#endif
#ifdef USE_SHEEN
	material.sheenColor = sheenColor;
	#ifdef USE_SHEEN_COLORMAP
		material.sheenColor *= texture2D( sheenColorMap, vSheenColorMapUv ).rgb;
	#endif
	material.sheenRoughness = clamp( sheenRoughness, 0.07, 1.0 );
	#ifdef USE_SHEEN_ROUGHNESSMAP
		material.sheenRoughness *= texture2D( sheenRoughnessMap, vSheenRoughnessMapUv ).a;
	#endif
#endif
#ifdef USE_ANISOTROPY
	#ifdef USE_ANISOTROPYMAP
		mat2 anisotropyMat = mat2( anisotropyVector.x, anisotropyVector.y, - anisotropyVector.y, anisotropyVector.x );
		vec3 anisotropyPolar = texture2D( anisotropyMap, vAnisotropyMapUv ).rgb;
		vec2 anisotropyV = anisotropyMat * normalize( 2.0 * anisotropyPolar.rg - vec2( 1.0 ) ) * anisotropyPolar.b;
	#else
		vec2 anisotropyV = anisotropyVector;
	#endif
	material.anisotropy = length( anisotropyV );
	if( material.anisotropy == 0.0 ) {
		anisotropyV = vec2( 1.0, 0.0 );
	} else {
		anisotropyV /= material.anisotropy;
		material.anisotropy = saturate( material.anisotropy );
	}
	material.alphaT = mix( pow2( material.roughness ), 1.0, pow2( material.anisotropy ) );
	material.anisotropyT = tbn[ 0 ] * anisotropyV.x + tbn[ 1 ] * anisotropyV.y;
	material.anisotropyB = tbn[ 1 ] * anisotropyV.x - tbn[ 0 ] * anisotropyV.y;
#endif`,My=`struct PhysicalMaterial {
	vec3 diffuseColor;
	float roughness;
	vec3 specularColor;
	float specularF90;
	#ifdef USE_CLEARCOAT
		float clearcoat;
		float clearcoatRoughness;
		vec3 clearcoatF0;
		float clearcoatF90;
	#endif
	#ifdef USE_IRIDESCENCE
		float iridescence;
		float iridescenceIOR;
		float iridescenceThickness;
		vec3 iridescenceFresnel;
		vec3 iridescenceF0;
	#endif
	#ifdef USE_SHEEN
		vec3 sheenColor;
		float sheenRoughness;
	#endif
	#ifdef IOR
		float ior;
	#endif
	#ifdef USE_TRANSMISSION
		float transmission;
		float transmissionAlpha;
		float thickness;
		float attenuationDistance;
		vec3 attenuationColor;
	#endif
	#ifdef USE_ANISOTROPY
		float anisotropy;
		float alphaT;
		vec3 anisotropyT;
		vec3 anisotropyB;
	#endif
};
vec3 clearcoatSpecularDirect = vec3( 0.0 );
vec3 clearcoatSpecularIndirect = vec3( 0.0 );
vec3 sheenSpecularDirect = vec3( 0.0 );
vec3 sheenSpecularIndirect = vec3(0.0 );
vec3 Schlick_to_F0( const in vec3 f, const in float f90, const in float dotVH ) {
    float x = clamp( 1.0 - dotVH, 0.0, 1.0 );
    float x2 = x * x;
    float x5 = clamp( x * x2 * x2, 0.0, 0.9999 );
    return ( f - vec3( f90 ) * x5 ) / ( 1.0 - x5 );
}
float V_GGX_SmithCorrelated( const in float alpha, const in float dotNL, const in float dotNV ) {
	float a2 = pow2( alpha );
	float gv = dotNL * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNV ) );
	float gl = dotNV * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNL ) );
	return 0.5 / max( gv + gl, EPSILON );
}
float D_GGX( const in float alpha, const in float dotNH ) {
	float a2 = pow2( alpha );
	float denom = pow2( dotNH ) * ( a2 - 1.0 ) + 1.0;
	return RECIPROCAL_PI * a2 / pow2( denom );
}
#ifdef USE_ANISOTROPY
	float V_GGX_SmithCorrelated_Anisotropic( const in float alphaT, const in float alphaB, const in float dotTV, const in float dotBV, const in float dotTL, const in float dotBL, const in float dotNV, const in float dotNL ) {
		float gv = dotNL * length( vec3( alphaT * dotTV, alphaB * dotBV, dotNV ) );
		float gl = dotNV * length( vec3( alphaT * dotTL, alphaB * dotBL, dotNL ) );
		float v = 0.5 / ( gv + gl );
		return saturate(v);
	}
	float D_GGX_Anisotropic( const in float alphaT, const in float alphaB, const in float dotNH, const in float dotTH, const in float dotBH ) {
		float a2 = alphaT * alphaB;
		highp vec3 v = vec3( alphaB * dotTH, alphaT * dotBH, a2 * dotNH );
		highp float v2 = dot( v, v );
		float w2 = a2 / v2;
		return RECIPROCAL_PI * a2 * pow2 ( w2 );
	}
#endif
#ifdef USE_CLEARCOAT
	vec3 BRDF_GGX_Clearcoat( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material) {
		vec3 f0 = material.clearcoatF0;
		float f90 = material.clearcoatF90;
		float roughness = material.clearcoatRoughness;
		float alpha = pow2( roughness );
		vec3 halfDir = normalize( lightDir + viewDir );
		float dotNL = saturate( dot( normal, lightDir ) );
		float dotNV = saturate( dot( normal, viewDir ) );
		float dotNH = saturate( dot( normal, halfDir ) );
		float dotVH = saturate( dot( viewDir, halfDir ) );
		vec3 F = F_Schlick( f0, f90, dotVH );
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
		return F * ( V * D );
	}
#endif
vec3 BRDF_GGX( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material ) {
	vec3 f0 = material.specularColor;
	float f90 = material.specularF90;
	float roughness = material.roughness;
	float alpha = pow2( roughness );
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( f0, f90, dotVH );
	#ifdef USE_IRIDESCENCE
		F = mix( F, material.iridescenceFresnel, material.iridescence );
	#endif
	#ifdef USE_ANISOTROPY
		float dotTL = dot( material.anisotropyT, lightDir );
		float dotTV = dot( material.anisotropyT, viewDir );
		float dotTH = dot( material.anisotropyT, halfDir );
		float dotBL = dot( material.anisotropyB, lightDir );
		float dotBV = dot( material.anisotropyB, viewDir );
		float dotBH = dot( material.anisotropyB, halfDir );
		float V = V_GGX_SmithCorrelated_Anisotropic( material.alphaT, alpha, dotTV, dotBV, dotTL, dotBL, dotNV, dotNL );
		float D = D_GGX_Anisotropic( material.alphaT, alpha, dotNH, dotTH, dotBH );
	#else
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
	#endif
	return F * ( V * D );
}
vec2 LTC_Uv( const in vec3 N, const in vec3 V, const in float roughness ) {
	const float LUT_SIZE = 64.0;
	const float LUT_SCALE = ( LUT_SIZE - 1.0 ) / LUT_SIZE;
	const float LUT_BIAS = 0.5 / LUT_SIZE;
	float dotNV = saturate( dot( N, V ) );
	vec2 uv = vec2( roughness, sqrt( 1.0 - dotNV ) );
	uv = uv * LUT_SCALE + LUT_BIAS;
	return uv;
}
float LTC_ClippedSphereFormFactor( const in vec3 f ) {
	float l = length( f );
	return max( ( l * l + f.z ) / ( l + 1.0 ), 0.0 );
}
vec3 LTC_EdgeVectorFormFactor( const in vec3 v1, const in vec3 v2 ) {
	float x = dot( v1, v2 );
	float y = abs( x );
	float a = 0.8543985 + ( 0.4965155 + 0.0145206 * y ) * y;
	float b = 3.4175940 + ( 4.1616724 + y ) * y;
	float v = a / b;
	float theta_sintheta = ( x > 0.0 ) ? v : 0.5 * inversesqrt( max( 1.0 - x * x, 1e-7 ) ) - v;
	return cross( v1, v2 ) * theta_sintheta;
}
vec3 LTC_Evaluate( const in vec3 N, const in vec3 V, const in vec3 P, const in mat3 mInv, const in vec3 rectCoords[ 4 ] ) {
	vec3 v1 = rectCoords[ 1 ] - rectCoords[ 0 ];
	vec3 v2 = rectCoords[ 3 ] - rectCoords[ 0 ];
	vec3 lightNormal = cross( v1, v2 );
	if( dot( lightNormal, P - rectCoords[ 0 ] ) < 0.0 ) return vec3( 0.0 );
	vec3 T1, T2;
	T1 = normalize( V - N * dot( V, N ) );
	T2 = - cross( N, T1 );
	mat3 mat = mInv * transposeMat3( mat3( T1, T2, N ) );
	vec3 coords[ 4 ];
	coords[ 0 ] = mat * ( rectCoords[ 0 ] - P );
	coords[ 1 ] = mat * ( rectCoords[ 1 ] - P );
	coords[ 2 ] = mat * ( rectCoords[ 2 ] - P );
	coords[ 3 ] = mat * ( rectCoords[ 3 ] - P );
	coords[ 0 ] = normalize( coords[ 0 ] );
	coords[ 1 ] = normalize( coords[ 1 ] );
	coords[ 2 ] = normalize( coords[ 2 ] );
	coords[ 3 ] = normalize( coords[ 3 ] );
	vec3 vectorFormFactor = vec3( 0.0 );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 0 ], coords[ 1 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 1 ], coords[ 2 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 2 ], coords[ 3 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 3 ], coords[ 0 ] );
	float result = LTC_ClippedSphereFormFactor( vectorFormFactor );
	return vec3( result );
}
#if defined( USE_SHEEN )
float D_Charlie( float roughness, float dotNH ) {
	float alpha = pow2( roughness );
	float invAlpha = 1.0 / alpha;
	float cos2h = dotNH * dotNH;
	float sin2h = max( 1.0 - cos2h, 0.0078125 );
	return ( 2.0 + invAlpha ) * pow( sin2h, invAlpha * 0.5 ) / ( 2.0 * PI );
}
float V_Neubelt( float dotNV, float dotNL ) {
	return saturate( 1.0 / ( 4.0 * ( dotNL + dotNV - dotNL * dotNV ) ) );
}
vec3 BRDF_Sheen( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, vec3 sheenColor, const in float sheenRoughness ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float D = D_Charlie( sheenRoughness, dotNH );
	float V = V_Neubelt( dotNV, dotNL );
	return sheenColor * ( D * V );
}
#endif
float IBLSheenBRDF( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	float r2 = roughness * roughness;
	float a = roughness < 0.25 ? -339.2 * r2 + 161.4 * roughness - 25.9 : -8.48 * r2 + 14.3 * roughness - 9.95;
	float b = roughness < 0.25 ? 44.0 * r2 - 23.7 * roughness + 3.26 : 1.97 * r2 - 3.27 * roughness + 0.72;
	float DG = exp( a * dotNV + b ) + ( roughness < 0.25 ? 0.0 : 0.1 * ( roughness - 0.25 ) );
	return saturate( DG * RECIPROCAL_PI );
}
vec2 DFGApprox( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	const vec4 c0 = vec4( - 1, - 0.0275, - 0.572, 0.022 );
	const vec4 c1 = vec4( 1, 0.0425, 1.04, - 0.04 );
	vec4 r = roughness * c0 + c1;
	float a004 = min( r.x * r.x, exp2( - 9.28 * dotNV ) ) * r.x + r.y;
	vec2 fab = vec2( - 1.04, 1.04 ) * a004 + r.zw;
	return fab;
}
vec3 EnvironmentBRDF( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness ) {
	vec2 fab = DFGApprox( normal, viewDir, roughness );
	return specularColor * fab.x + specularF90 * fab.y;
}
#ifdef USE_IRIDESCENCE
void computeMultiscatteringIridescence( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float iridescence, const in vec3 iridescenceF0, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#else
void computeMultiscattering( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#endif
	vec2 fab = DFGApprox( normal, viewDir, roughness );
	#ifdef USE_IRIDESCENCE
		vec3 Fr = mix( specularColor, iridescenceF0, iridescence );
	#else
		vec3 Fr = specularColor;
	#endif
	vec3 FssEss = Fr * fab.x + specularF90 * fab.y;
	float Ess = fab.x + fab.y;
	float Ems = 1.0 - Ess;
	vec3 Favg = Fr + ( 1.0 - Fr ) * 0.047619;	vec3 Fms = FssEss * Favg / ( 1.0 - Ems * Favg );
	singleScatter += FssEss;
	multiScatter += Fms * Ems;
}
#if NUM_RECT_AREA_LIGHTS > 0
	void RE_Direct_RectArea_Physical( const in RectAreaLight rectAreaLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
		vec3 normal = geometryNormal;
		vec3 viewDir = geometryViewDir;
		vec3 position = geometryPosition;
		vec3 lightPos = rectAreaLight.position;
		vec3 halfWidth = rectAreaLight.halfWidth;
		vec3 halfHeight = rectAreaLight.halfHeight;
		vec3 lightColor = rectAreaLight.color;
		float roughness = material.roughness;
		vec3 rectCoords[ 4 ];
		rectCoords[ 0 ] = lightPos + halfWidth - halfHeight;		rectCoords[ 1 ] = lightPos - halfWidth - halfHeight;
		rectCoords[ 2 ] = lightPos - halfWidth + halfHeight;
		rectCoords[ 3 ] = lightPos + halfWidth + halfHeight;
		vec2 uv = LTC_Uv( normal, viewDir, roughness );
		vec4 t1 = texture2D( ltc_1, uv );
		vec4 t2 = texture2D( ltc_2, uv );
		mat3 mInv = mat3(
			vec3( t1.x, 0, t1.y ),
			vec3(    0, 1,    0 ),
			vec3( t1.z, 0, t1.w )
		);
		vec3 fresnel = ( material.specularColor * t2.x + ( vec3( 1.0 ) - material.specularColor ) * t2.y );
		reflectedLight.directSpecular += lightColor * fresnel * LTC_Evaluate( normal, viewDir, position, mInv, rectCoords );
		reflectedLight.directDiffuse += lightColor * material.diffuseColor * LTC_Evaluate( normal, viewDir, position, mat3( 1.0 ), rectCoords );
	}
#endif
void RE_Direct_Physical( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	#ifdef USE_CLEARCOAT
		float dotNLcc = saturate( dot( geometryClearcoatNormal, directLight.direction ) );
		vec3 ccIrradiance = dotNLcc * directLight.color;
		clearcoatSpecularDirect += ccIrradiance * BRDF_GGX_Clearcoat( directLight.direction, geometryViewDir, geometryClearcoatNormal, material );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularDirect += irradiance * BRDF_Sheen( directLight.direction, geometryViewDir, geometryNormal, material.sheenColor, material.sheenRoughness );
	#endif
	reflectedLight.directSpecular += irradiance * BRDF_GGX( directLight.direction, geometryViewDir, geometryNormal, material );
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Physical( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectSpecular_Physical( const in vec3 radiance, const in vec3 irradiance, const in vec3 clearcoatRadiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight) {
	#ifdef USE_CLEARCOAT
		clearcoatSpecularIndirect += clearcoatRadiance * EnvironmentBRDF( geometryClearcoatNormal, geometryViewDir, material.clearcoatF0, material.clearcoatF90, material.clearcoatRoughness );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularIndirect += irradiance * material.sheenColor * IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
	#endif
	vec3 singleScattering = vec3( 0.0 );
	vec3 multiScattering = vec3( 0.0 );
	vec3 cosineWeightedIrradiance = irradiance * RECIPROCAL_PI;
	#ifdef USE_IRIDESCENCE
		computeMultiscatteringIridescence( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.iridescence, material.iridescenceFresnel, material.roughness, singleScattering, multiScattering );
	#else
		computeMultiscattering( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.roughness, singleScattering, multiScattering );
	#endif
	vec3 totalScattering = singleScattering + multiScattering;
	vec3 diffuse = material.diffuseColor * ( 1.0 - max( max( totalScattering.r, totalScattering.g ), totalScattering.b ) );
	reflectedLight.indirectSpecular += radiance * singleScattering;
	reflectedLight.indirectSpecular += multiScattering * cosineWeightedIrradiance;
	reflectedLight.indirectDiffuse += diffuse * cosineWeightedIrradiance;
}
#define RE_Direct				RE_Direct_Physical
#define RE_Direct_RectArea		RE_Direct_RectArea_Physical
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Physical
#define RE_IndirectSpecular		RE_IndirectSpecular_Physical
float computeSpecularOcclusion( const in float dotNV, const in float ambientOcclusion, const in float roughness ) {
	return saturate( pow( dotNV + ambientOcclusion, exp2( - 16.0 * roughness - 1.0 ) ) - 1.0 + ambientOcclusion );
}`,Ey=`
vec3 geometryPosition = - vViewPosition;
vec3 geometryNormal = normal;
vec3 geometryViewDir = ( isOrthographic ) ? vec3( 0, 0, 1 ) : normalize( vViewPosition );
vec3 geometryClearcoatNormal = vec3( 0.0 );
#ifdef USE_CLEARCOAT
	geometryClearcoatNormal = clearcoatNormal;
#endif
#ifdef USE_IRIDESCENCE
	float dotNVi = saturate( dot( normal, geometryViewDir ) );
	if ( material.iridescenceThickness == 0.0 ) {
		material.iridescence = 0.0;
	} else {
		material.iridescence = saturate( material.iridescence );
	}
	if ( material.iridescence > 0.0 ) {
		material.iridescenceFresnel = evalIridescence( 1.0, material.iridescenceIOR, dotNVi, material.iridescenceThickness, material.specularColor );
		material.iridescenceF0 = Schlick_to_F0( material.iridescenceFresnel, 1.0, dotNVi );
	}
#endif
IncidentLight directLight;
#if ( NUM_POINT_LIGHTS > 0 ) && defined( RE_Direct )
	PointLight pointLight;
	#if defined( USE_SHADOWMAP ) && NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHTS; i ++ ) {
		pointLight = pointLights[ i ];
		getPointLightInfo( pointLight, geometryPosition, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_POINT_LIGHT_SHADOWS )
		pointLightShadow = pointLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getPointShadow( pointShadowMap[ i ], pointLightShadow.shadowMapSize, pointLightShadow.shadowBias, pointLightShadow.shadowRadius, vPointShadowCoord[ i ], pointLightShadow.shadowCameraNear, pointLightShadow.shadowCameraFar ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_SPOT_LIGHTS > 0 ) && defined( RE_Direct )
	SpotLight spotLight;
	vec4 spotColor;
	vec3 spotLightCoord;
	bool inSpotLightMap;
	#if defined( USE_SHADOWMAP ) && NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHTS; i ++ ) {
		spotLight = spotLights[ i ];
		getSpotLightInfo( spotLight, geometryPosition, directLight );
		#if ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#define SPOT_LIGHT_MAP_INDEX UNROLLED_LOOP_INDEX
		#elif ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		#define SPOT_LIGHT_MAP_INDEX NUM_SPOT_LIGHT_MAPS
		#else
		#define SPOT_LIGHT_MAP_INDEX ( UNROLLED_LOOP_INDEX - NUM_SPOT_LIGHT_SHADOWS + NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#endif
		#if ( SPOT_LIGHT_MAP_INDEX < NUM_SPOT_LIGHT_MAPS )
			spotLightCoord = vSpotLightCoord[ i ].xyz / vSpotLightCoord[ i ].w;
			inSpotLightMap = all( lessThan( abs( spotLightCoord * 2. - 1. ), vec3( 1.0 ) ) );
			spotColor = texture2D( spotLightMap[ SPOT_LIGHT_MAP_INDEX ], spotLightCoord.xy );
			directLight.color = inSpotLightMap ? directLight.color * spotColor.rgb : directLight.color;
		#endif
		#undef SPOT_LIGHT_MAP_INDEX
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		spotLightShadow = spotLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( spotShadowMap[ i ], spotLightShadow.shadowMapSize, spotLightShadow.shadowBias, spotLightShadow.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )
	DirectionalLight directionalLight;
	#if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHTS; i ++ ) {
		directionalLight = directionalLights[ i ];
		getDirectionalLightInfo( directionalLight, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_DIR_LIGHT_SHADOWS )
		directionalLightShadow = directionalLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( directionalShadowMap[ i ], directionalLightShadow.shadowMapSize, directionalLightShadow.shadowBias, directionalLightShadow.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_RECT_AREA_LIGHTS > 0 ) && defined( RE_Direct_RectArea )
	RectAreaLight rectAreaLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_RECT_AREA_LIGHTS; i ++ ) {
		rectAreaLight = rectAreaLights[ i ];
		RE_Direct_RectArea( rectAreaLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if defined( RE_IndirectDiffuse )
	vec3 iblIrradiance = vec3( 0.0 );
	vec3 irradiance = getAmbientLightIrradiance( ambientLightColor );
	#if defined( USE_LIGHT_PROBES )
		irradiance += getLightProbeIrradiance( lightProbe, geometryNormal );
	#endif
	#if ( NUM_HEMI_LIGHTS > 0 )
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_HEMI_LIGHTS; i ++ ) {
			irradiance += getHemisphereLightIrradiance( hemisphereLights[ i ], geometryNormal );
		}
		#pragma unroll_loop_end
	#endif
#endif
#if defined( RE_IndirectSpecular )
	vec3 radiance = vec3( 0.0 );
	vec3 clearcoatRadiance = vec3( 0.0 );
#endif`,by=`#if defined( RE_IndirectDiffuse )
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapIntensity;
		irradiance += lightMapIrradiance;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD ) && defined( ENVMAP_TYPE_CUBE_UV )
		iblIrradiance += getIBLIrradiance( geometryNormal );
	#endif
#endif
#if defined( USE_ENVMAP ) && defined( RE_IndirectSpecular )
	#ifdef USE_ANISOTROPY
		radiance += getIBLAnisotropyRadiance( geometryViewDir, geometryNormal, material.roughness, material.anisotropyB, material.anisotropy );
	#else
		radiance += getIBLRadiance( geometryViewDir, geometryNormal, material.roughness );
	#endif
	#ifdef USE_CLEARCOAT
		clearcoatRadiance += getIBLRadiance( geometryViewDir, geometryClearcoatNormal, material.clearcoatRoughness );
	#endif
#endif`,Ty=`#if defined( RE_IndirectDiffuse )
	RE_IndirectDiffuse( irradiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif
#if defined( RE_IndirectSpecular )
	RE_IndirectSpecular( radiance, iblIrradiance, clearcoatRadiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif`,Ay=`#if defined( USE_LOGDEPTHBUF ) && defined( USE_LOGDEPTHBUF_EXT )
	gl_FragDepthEXT = vIsPerspective == 0.0 ? gl_FragCoord.z : log2( vFragDepth ) * logDepthBufFC * 0.5;
#endif`,wy=`#if defined( USE_LOGDEPTHBUF ) && defined( USE_LOGDEPTHBUF_EXT )
	uniform float logDepthBufFC;
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,Ry=`#ifdef USE_LOGDEPTHBUF
	#ifdef USE_LOGDEPTHBUF_EXT
		varying float vFragDepth;
		varying float vIsPerspective;
	#else
		uniform float logDepthBufFC;
	#endif
#endif`,Cy=`#ifdef USE_LOGDEPTHBUF
	#ifdef USE_LOGDEPTHBUF_EXT
		vFragDepth = 1.0 + gl_Position.w;
		vIsPerspective = float( isPerspectiveMatrix( projectionMatrix ) );
	#else
		if ( isPerspectiveMatrix( projectionMatrix ) ) {
			gl_Position.z = log2( max( EPSILON, gl_Position.w + 1.0 ) ) * logDepthBufFC - 1.0;
			gl_Position.z *= gl_Position.w;
		}
	#endif
#endif`,Py=`#ifdef USE_MAP
	vec4 sampledDiffuseColor = texture2D( map, vMapUv );
	#ifdef DECODE_VIDEO_TEXTURE
		sampledDiffuseColor = vec4( mix( pow( sampledDiffuseColor.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), sampledDiffuseColor.rgb * 0.0773993808, vec3( lessThanEqual( sampledDiffuseColor.rgb, vec3( 0.04045 ) ) ) ), sampledDiffuseColor.w );
	
	#endif
	diffuseColor *= sampledDiffuseColor;
#endif`,Ly=`#ifdef USE_MAP
	uniform sampler2D map;
#endif`,Dy=`#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
	#if defined( USE_POINTS_UV )
		vec2 uv = vUv;
	#else
		vec2 uv = ( uvTransform * vec3( gl_PointCoord.x, 1.0 - gl_PointCoord.y, 1 ) ).xy;
	#endif
#endif
#ifdef USE_MAP
	diffuseColor *= texture2D( map, uv );
#endif
#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, uv ).g;
#endif`,Uy=`#if defined( USE_POINTS_UV )
	varying vec2 vUv;
#else
	#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
		uniform mat3 uvTransform;
	#endif
#endif
#ifdef USE_MAP
	uniform sampler2D map;
#endif
#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,Iy=`float metalnessFactor = metalness;
#ifdef USE_METALNESSMAP
	vec4 texelMetalness = texture2D( metalnessMap, vMetalnessMapUv );
	metalnessFactor *= texelMetalness.b;
#endif`,Oy=`#ifdef USE_METALNESSMAP
	uniform sampler2D metalnessMap;
#endif`,Ny=`#if defined( USE_MORPHCOLORS ) && defined( MORPHTARGETS_TEXTURE )
	vColor *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		#if defined( USE_COLOR_ALPHA )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ) * morphTargetInfluences[ i ];
		#elif defined( USE_COLOR )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ).rgb * morphTargetInfluences[ i ];
		#endif
	}
#endif`,Fy=`#ifdef USE_MORPHNORMALS
	objectNormal *= morphTargetBaseInfluence;
	#ifdef MORPHTARGETS_TEXTURE
		for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
			if ( morphTargetInfluences[ i ] != 0.0 ) objectNormal += getMorph( gl_VertexID, i, 1 ).xyz * morphTargetInfluences[ i ];
		}
	#else
		objectNormal += morphNormal0 * morphTargetInfluences[ 0 ];
		objectNormal += morphNormal1 * morphTargetInfluences[ 1 ];
		objectNormal += morphNormal2 * morphTargetInfluences[ 2 ];
		objectNormal += morphNormal3 * morphTargetInfluences[ 3 ];
	#endif
#endif`,zy=`#ifdef USE_MORPHTARGETS
	uniform float morphTargetBaseInfluence;
	#ifdef MORPHTARGETS_TEXTURE
		uniform float morphTargetInfluences[ MORPHTARGETS_COUNT ];
		uniform sampler2DArray morphTargetsTexture;
		uniform ivec2 morphTargetsTextureSize;
		vec4 getMorph( const in int vertexIndex, const in int morphTargetIndex, const in int offset ) {
			int texelIndex = vertexIndex * MORPHTARGETS_TEXTURE_STRIDE + offset;
			int y = texelIndex / morphTargetsTextureSize.x;
			int x = texelIndex - y * morphTargetsTextureSize.x;
			ivec3 morphUV = ivec3( x, y, morphTargetIndex );
			return texelFetch( morphTargetsTexture, morphUV, 0 );
		}
	#else
		#ifndef USE_MORPHNORMALS
			uniform float morphTargetInfluences[ 8 ];
		#else
			uniform float morphTargetInfluences[ 4 ];
		#endif
	#endif
#endif`,By=`#ifdef USE_MORPHTARGETS
	transformed *= morphTargetBaseInfluence;
	#ifdef MORPHTARGETS_TEXTURE
		for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
			if ( morphTargetInfluences[ i ] != 0.0 ) transformed += getMorph( gl_VertexID, i, 0 ).xyz * morphTargetInfluences[ i ];
		}
	#else
		transformed += morphTarget0 * morphTargetInfluences[ 0 ];
		transformed += morphTarget1 * morphTargetInfluences[ 1 ];
		transformed += morphTarget2 * morphTargetInfluences[ 2 ];
		transformed += morphTarget3 * morphTargetInfluences[ 3 ];
		#ifndef USE_MORPHNORMALS
			transformed += morphTarget4 * morphTargetInfluences[ 4 ];
			transformed += morphTarget5 * morphTargetInfluences[ 5 ];
			transformed += morphTarget6 * morphTargetInfluences[ 6 ];
			transformed += morphTarget7 * morphTargetInfluences[ 7 ];
		#endif
	#endif
#endif`,ky=`float faceDirection = gl_FrontFacing ? 1.0 : - 1.0;
#ifdef FLAT_SHADED
	vec3 fdx = dFdx( vViewPosition );
	vec3 fdy = dFdy( vViewPosition );
	vec3 normal = normalize( cross( fdx, fdy ) );
#else
	vec3 normal = normalize( vNormal );
	#ifdef DOUBLE_SIDED
		normal *= faceDirection;
	#endif
#endif
#if defined( USE_NORMALMAP_TANGENTSPACE ) || defined( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY )
	#ifdef USE_TANGENT
		mat3 tbn = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn = getTangentFrame( - vViewPosition, normal,
		#if defined( USE_NORMALMAP )
			vNormalMapUv
		#elif defined( USE_CLEARCOAT_NORMALMAP )
			vClearcoatNormalMapUv
		#else
			vUv
		#endif
		);
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn[0] *= faceDirection;
		tbn[1] *= faceDirection;
	#endif
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	#ifdef USE_TANGENT
		mat3 tbn2 = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn2 = getTangentFrame( - vViewPosition, normal, vClearcoatNormalMapUv );
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn2[0] *= faceDirection;
		tbn2[1] *= faceDirection;
	#endif
#endif
vec3 nonPerturbedNormal = normal;`,Vy=`#ifdef USE_NORMALMAP_OBJECTSPACE
	normal = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	#ifdef FLIP_SIDED
		normal = - normal;
	#endif
	#ifdef DOUBLE_SIDED
		normal = normal * faceDirection;
	#endif
	normal = normalize( normalMatrix * normal );
#elif defined( USE_NORMALMAP_TANGENTSPACE )
	vec3 mapN = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	mapN.xy *= normalScale;
	normal = normalize( tbn * mapN );
#elif defined( USE_BUMPMAP )
	normal = perturbNormalArb( - vViewPosition, normal, dHdxy_fwd(), faceDirection );
#endif`,Hy=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,Gy=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,Wy=`#ifndef FLAT_SHADED
	vNormal = normalize( transformedNormal );
	#ifdef USE_TANGENT
		vTangent = normalize( transformedTangent );
		vBitangent = normalize( cross( vNormal, vTangent ) * tangent.w );
	#endif
#endif`,Xy=`#ifdef USE_NORMALMAP
	uniform sampler2D normalMap;
	uniform vec2 normalScale;
#endif
#ifdef USE_NORMALMAP_OBJECTSPACE
	uniform mat3 normalMatrix;
#endif
#if ! defined ( USE_TANGENT ) && ( defined ( USE_NORMALMAP_TANGENTSPACE ) || defined ( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY ) )
	mat3 getTangentFrame( vec3 eye_pos, vec3 surf_norm, vec2 uv ) {
		vec3 q0 = dFdx( eye_pos.xyz );
		vec3 q1 = dFdy( eye_pos.xyz );
		vec2 st0 = dFdx( uv.st );
		vec2 st1 = dFdy( uv.st );
		vec3 N = surf_norm;
		vec3 q1perp = cross( q1, N );
		vec3 q0perp = cross( N, q0 );
		vec3 T = q1perp * st0.x + q0perp * st1.x;
		vec3 B = q1perp * st0.y + q0perp * st1.y;
		float det = max( dot( T, T ), dot( B, B ) );
		float scale = ( det == 0.0 ) ? 0.0 : inversesqrt( det );
		return mat3( T * scale, B * scale, N );
	}
#endif`,qy=`#ifdef USE_CLEARCOAT
	vec3 clearcoatNormal = nonPerturbedNormal;
#endif`,Yy=`#ifdef USE_CLEARCOAT_NORMALMAP
	vec3 clearcoatMapN = texture2D( clearcoatNormalMap, vClearcoatNormalMapUv ).xyz * 2.0 - 1.0;
	clearcoatMapN.xy *= clearcoatNormalScale;
	clearcoatNormal = normalize( tbn2 * clearcoatMapN );
#endif`,$y=`#ifdef USE_CLEARCOATMAP
	uniform sampler2D clearcoatMap;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform sampler2D clearcoatNormalMap;
	uniform vec2 clearcoatNormalScale;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform sampler2D clearcoatRoughnessMap;
#endif`,jy=`#ifdef USE_IRIDESCENCEMAP
	uniform sampler2D iridescenceMap;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform sampler2D iridescenceThicknessMap;
#endif`,Ky=`#ifdef OPAQUE
diffuseColor.a = 1.0;
#endif
#ifdef USE_TRANSMISSION
diffuseColor.a *= material.transmissionAlpha;
#endif
gl_FragColor = vec4( outgoingLight, diffuseColor.a );`,Zy=`vec3 packNormalToRGB( const in vec3 normal ) {
	return normalize( normal ) * 0.5 + 0.5;
}
vec3 unpackRGBToNormal( const in vec3 rgb ) {
	return 2.0 * rgb.xyz - 1.0;
}
const float PackUpscale = 256. / 255.;const float UnpackDownscale = 255. / 256.;
const vec3 PackFactors = vec3( 256. * 256. * 256., 256. * 256., 256. );
const vec4 UnpackFactors = UnpackDownscale / vec4( PackFactors, 1. );
const float ShiftRight8 = 1. / 256.;
vec4 packDepthToRGBA( const in float v ) {
	vec4 r = vec4( fract( v * PackFactors ), v );
	r.yzw -= r.xyz * ShiftRight8;	return r * PackUpscale;
}
float unpackRGBAToDepth( const in vec4 v ) {
	return dot( v, UnpackFactors );
}
vec2 packDepthToRG( in highp float v ) {
	return packDepthToRGBA( v ).yx;
}
float unpackRGToDepth( const in highp vec2 v ) {
	return unpackRGBAToDepth( vec4( v.xy, 0.0, 0.0 ) );
}
vec4 pack2HalfToRGBA( vec2 v ) {
	vec4 r = vec4( v.x, fract( v.x * 255.0 ), v.y, fract( v.y * 255.0 ) );
	return vec4( r.x - r.y / 255.0, r.y, r.z - r.w / 255.0, r.w );
}
vec2 unpackRGBATo2Half( vec4 v ) {
	return vec2( v.x + ( v.y / 255.0 ), v.z + ( v.w / 255.0 ) );
}
float viewZToOrthographicDepth( const in float viewZ, const in float near, const in float far ) {
	return ( viewZ + near ) / ( near - far );
}
float orthographicDepthToViewZ( const in float depth, const in float near, const in float far ) {
	return depth * ( near - far ) - near;
}
float viewZToPerspectiveDepth( const in float viewZ, const in float near, const in float far ) {
	return ( ( near + viewZ ) * far ) / ( ( far - near ) * viewZ );
}
float perspectiveDepthToViewZ( const in float depth, const in float near, const in float far ) {
	return ( near * far ) / ( ( far - near ) * depth - far );
}`,Jy=`#ifdef PREMULTIPLIED_ALPHA
	gl_FragColor.rgb *= gl_FragColor.a;
#endif`,Qy=`vec4 mvPosition = vec4( transformed, 1.0 );
#ifdef USE_BATCHING
	mvPosition = batchingMatrix * mvPosition;
#endif
#ifdef USE_INSTANCING
	mvPosition = instanceMatrix * mvPosition;
#endif
mvPosition = modelViewMatrix * mvPosition;
gl_Position = projectionMatrix * mvPosition;`,eS=`#ifdef DITHERING
	gl_FragColor.rgb = dithering( gl_FragColor.rgb );
#endif`,tS=`#ifdef DITHERING
	vec3 dithering( vec3 color ) {
		float grid_position = rand( gl_FragCoord.xy );
		vec3 dither_shift_RGB = vec3( 0.25 / 255.0, -0.25 / 255.0, 0.25 / 255.0 );
		dither_shift_RGB = mix( 2.0 * dither_shift_RGB, -2.0 * dither_shift_RGB, grid_position );
		return color + dither_shift_RGB;
	}
#endif`,nS=`float roughnessFactor = roughness;
#ifdef USE_ROUGHNESSMAP
	vec4 texelRoughness = texture2D( roughnessMap, vRoughnessMapUv );
	roughnessFactor *= texelRoughness.g;
#endif`,iS=`#ifdef USE_ROUGHNESSMAP
	uniform sampler2D roughnessMap;
#endif`,sS=`#if NUM_SPOT_LIGHT_COORDS > 0
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#if NUM_SPOT_LIGHT_MAPS > 0
	uniform sampler2D spotLightMap[ NUM_SPOT_LIGHT_MAPS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform sampler2D directionalShadowMap[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		uniform sampler2D spotShadowMap[ NUM_SPOT_LIGHT_SHADOWS ];
		struct SpotLightShadow {
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform sampler2D pointShadowMap[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
	float texture2DCompare( sampler2D depths, vec2 uv, float compare ) {
		return step( compare, unpackRGBAToDepth( texture2D( depths, uv ) ) );
	}
	vec2 texture2DDistribution( sampler2D shadow, vec2 uv ) {
		return unpackRGBATo2Half( texture2D( shadow, uv ) );
	}
	float VSMShadow (sampler2D shadow, vec2 uv, float compare ){
		float occlusion = 1.0;
		vec2 distribution = texture2DDistribution( shadow, uv );
		float hard_shadow = step( compare , distribution.x );
		if (hard_shadow != 1.0 ) {
			float distance = compare - distribution.x ;
			float variance = max( 0.00000, distribution.y * distribution.y );
			float softness_probability = variance / (variance + distance * distance );			softness_probability = clamp( ( softness_probability - 0.3 ) / ( 0.95 - 0.3 ), 0.0, 1.0 );			occlusion = clamp( max( hard_shadow, softness_probability ), 0.0, 1.0 );
		}
		return occlusion;
	}
	float getShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
		float shadow = 1.0;
		shadowCoord.xyz /= shadowCoord.w;
		shadowCoord.z += shadowBias;
		bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
		bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
		if ( frustumTest ) {
		#if defined( SHADOWMAP_TYPE_PCF )
			vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
			float dx0 = - texelSize.x * shadowRadius;
			float dy0 = - texelSize.y * shadowRadius;
			float dx1 = + texelSize.x * shadowRadius;
			float dy1 = + texelSize.y * shadowRadius;
			float dx2 = dx0 / 2.0;
			float dy2 = dy0 / 2.0;
			float dx3 = dx1 / 2.0;
			float dy3 = dy1 / 2.0;
			shadow = (
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy, shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, dy1 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy1 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, dy1 ), shadowCoord.z )
			) * ( 1.0 / 17.0 );
		#elif defined( SHADOWMAP_TYPE_PCF_SOFT )
			vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
			float dx = texelSize.x;
			float dy = texelSize.y;
			vec2 uv = shadowCoord.xy;
			vec2 f = fract( uv * shadowMapSize + 0.5 );
			uv -= f * texelSize;
			shadow = (
				texture2DCompare( shadowMap, uv, shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + vec2( dx, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + vec2( 0.0, dy ), shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + texelSize, shadowCoord.z ) +
				mix( texture2DCompare( shadowMap, uv + vec2( -dx, 0.0 ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, 0.0 ), shadowCoord.z ),
					 f.x ) +
				mix( texture2DCompare( shadowMap, uv + vec2( -dx, dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, dy ), shadowCoord.z ),
					 f.x ) +
				mix( texture2DCompare( shadowMap, uv + vec2( 0.0, -dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 0.0, 2.0 * dy ), shadowCoord.z ),
					 f.y ) +
				mix( texture2DCompare( shadowMap, uv + vec2( dx, -dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( dx, 2.0 * dy ), shadowCoord.z ),
					 f.y ) +
				mix( mix( texture2DCompare( shadowMap, uv + vec2( -dx, -dy ), shadowCoord.z ),
						  texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, -dy ), shadowCoord.z ),
						  f.x ),
					 mix( texture2DCompare( shadowMap, uv + vec2( -dx, 2.0 * dy ), shadowCoord.z ),
						  texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, 2.0 * dy ), shadowCoord.z ),
						  f.x ),
					 f.y )
			) * ( 1.0 / 9.0 );
		#elif defined( SHADOWMAP_TYPE_VSM )
			shadow = VSMShadow( shadowMap, shadowCoord.xy, shadowCoord.z );
		#else
			shadow = texture2DCompare( shadowMap, shadowCoord.xy, shadowCoord.z );
		#endif
		}
		return shadow;
	}
	vec2 cubeToUV( vec3 v, float texelSizeY ) {
		vec3 absV = abs( v );
		float scaleToCube = 1.0 / max( absV.x, max( absV.y, absV.z ) );
		absV *= scaleToCube;
		v *= scaleToCube * ( 1.0 - 2.0 * texelSizeY );
		vec2 planar = v.xy;
		float almostATexel = 1.5 * texelSizeY;
		float almostOne = 1.0 - almostATexel;
		if ( absV.z >= almostOne ) {
			if ( v.z > 0.0 )
				planar.x = 4.0 - v.x;
		} else if ( absV.x >= almostOne ) {
			float signX = sign( v.x );
			planar.x = v.z * signX + 2.0 * signX;
		} else if ( absV.y >= almostOne ) {
			float signY = sign( v.y );
			planar.x = v.x + 2.0 * signY + 2.0;
			planar.y = v.z * signY - 2.0;
		}
		return vec2( 0.125, 0.25 ) * planar + vec2( 0.375, 0.75 );
	}
	float getPointShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowBias, float shadowRadius, vec4 shadowCoord, float shadowCameraNear, float shadowCameraFar ) {
		vec2 texelSize = vec2( 1.0 ) / ( shadowMapSize * vec2( 4.0, 2.0 ) );
		vec3 lightToPosition = shadowCoord.xyz;
		float dp = ( length( lightToPosition ) - shadowCameraNear ) / ( shadowCameraFar - shadowCameraNear );		dp += shadowBias;
		vec3 bd3D = normalize( lightToPosition );
		#if defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_PCF_SOFT ) || defined( SHADOWMAP_TYPE_VSM )
			vec2 offset = vec2( - 1, 1 ) * shadowRadius * texelSize.y;
			return (
				texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xyy, texelSize.y ), dp ) +
				texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yyy, texelSize.y ), dp ) +
				texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xyx, texelSize.y ), dp ) +
				texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yyx, texelSize.y ), dp ) +
				texture2DCompare( shadowMap, cubeToUV( bd3D, texelSize.y ), dp ) +
				texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xxy, texelSize.y ), dp ) +
				texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yxy, texelSize.y ), dp ) +
				texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xxx, texelSize.y ), dp ) +
				texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yxx, texelSize.y ), dp )
			) * ( 1.0 / 9.0 );
		#else
			return texture2DCompare( shadowMap, cubeToUV( bd3D, texelSize.y ), dp );
		#endif
	}
#endif`,rS=`#if NUM_SPOT_LIGHT_COORDS > 0
	uniform mat4 spotLightMatrix[ NUM_SPOT_LIGHT_COORDS ];
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform mat4 directionalShadowMatrix[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		struct SpotLightShadow {
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform mat4 pointShadowMatrix[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
#endif`,oS=`#if ( defined( USE_SHADOWMAP ) && ( NUM_DIR_LIGHT_SHADOWS > 0 || NUM_POINT_LIGHT_SHADOWS > 0 ) ) || ( NUM_SPOT_LIGHT_COORDS > 0 )
	vec3 shadowWorldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
	vec4 shadowWorldPosition;
#endif
#if defined( USE_SHADOWMAP )
	#if NUM_DIR_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * directionalLightShadows[ i ].shadowNormalBias, 0 );
			vDirectionalShadowCoord[ i ] = directionalShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * pointLightShadows[ i ].shadowNormalBias, 0 );
			vPointShadowCoord[ i ] = pointShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
#endif
#if NUM_SPOT_LIGHT_COORDS > 0
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_COORDS; i ++ ) {
		shadowWorldPosition = worldPosition;
		#if ( defined( USE_SHADOWMAP ) && UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
			shadowWorldPosition.xyz += shadowWorldNormal * spotLightShadows[ i ].shadowNormalBias;
		#endif
		vSpotLightCoord[ i ] = spotLightMatrix[ i ] * shadowWorldPosition;
	}
	#pragma unroll_loop_end
#endif`,aS=`float getShadowMask() {
	float shadow = 1.0;
	#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
		directionalLight = directionalLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( directionalShadowMap[ i ], directionalLight.shadowMapSize, directionalLight.shadowBias, directionalLight.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_SHADOWS; i ++ ) {
		spotLight = spotLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( spotShadowMap[ i ], spotLight.shadowMapSize, spotLight.shadowBias, spotLight.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
		pointLight = pointLightShadows[ i ];
		shadow *= receiveShadow ? getPointShadow( pointShadowMap[ i ], pointLight.shadowMapSize, pointLight.shadowBias, pointLight.shadowRadius, vPointShadowCoord[ i ], pointLight.shadowCameraNear, pointLight.shadowCameraFar ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#endif
	return shadow;
}`,lS=`#ifdef USE_SKINNING
	mat4 boneMatX = getBoneMatrix( skinIndex.x );
	mat4 boneMatY = getBoneMatrix( skinIndex.y );
	mat4 boneMatZ = getBoneMatrix( skinIndex.z );
	mat4 boneMatW = getBoneMatrix( skinIndex.w );
#endif`,cS=`#ifdef USE_SKINNING
	uniform mat4 bindMatrix;
	uniform mat4 bindMatrixInverse;
	uniform highp sampler2D boneTexture;
	mat4 getBoneMatrix( const in float i ) {
		int size = textureSize( boneTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( boneTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( boneTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( boneTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( boneTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
#endif`,uS=`#ifdef USE_SKINNING
	vec4 skinVertex = bindMatrix * vec4( transformed, 1.0 );
	vec4 skinned = vec4( 0.0 );
	skinned += boneMatX * skinVertex * skinWeight.x;
	skinned += boneMatY * skinVertex * skinWeight.y;
	skinned += boneMatZ * skinVertex * skinWeight.z;
	skinned += boneMatW * skinVertex * skinWeight.w;
	transformed = ( bindMatrixInverse * skinned ).xyz;
#endif`,fS=`#ifdef USE_SKINNING
	mat4 skinMatrix = mat4( 0.0 );
	skinMatrix += skinWeight.x * boneMatX;
	skinMatrix += skinWeight.y * boneMatY;
	skinMatrix += skinWeight.z * boneMatZ;
	skinMatrix += skinWeight.w * boneMatW;
	skinMatrix = bindMatrixInverse * skinMatrix * bindMatrix;
	objectNormal = vec4( skinMatrix * vec4( objectNormal, 0.0 ) ).xyz;
	#ifdef USE_TANGENT
		objectTangent = vec4( skinMatrix * vec4( objectTangent, 0.0 ) ).xyz;
	#endif
#endif`,hS=`float specularStrength;
#ifdef USE_SPECULARMAP
	vec4 texelSpecular = texture2D( specularMap, vSpecularMapUv );
	specularStrength = texelSpecular.r;
#else
	specularStrength = 1.0;
#endif`,dS=`#ifdef USE_SPECULARMAP
	uniform sampler2D specularMap;
#endif`,pS=`#if defined( TONE_MAPPING )
	gl_FragColor.rgb = toneMapping( gl_FragColor.rgb );
#endif`,mS=`#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
uniform float toneMappingExposure;
vec3 LinearToneMapping( vec3 color ) {
	return saturate( toneMappingExposure * color );
}
vec3 ReinhardToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	return saturate( color / ( vec3( 1.0 ) + color ) );
}
vec3 OptimizedCineonToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	color = max( vec3( 0.0 ), color - 0.004 );
	return pow( ( color * ( 6.2 * color + 0.5 ) ) / ( color * ( 6.2 * color + 1.7 ) + 0.06 ), vec3( 2.2 ) );
}
vec3 RRTAndODTFit( vec3 v ) {
	vec3 a = v * ( v + 0.0245786 ) - 0.000090537;
	vec3 b = v * ( 0.983729 * v + 0.4329510 ) + 0.238081;
	return a / b;
}
vec3 ACESFilmicToneMapping( vec3 color ) {
	const mat3 ACESInputMat = mat3(
		vec3( 0.59719, 0.07600, 0.02840 ),		vec3( 0.35458, 0.90834, 0.13383 ),
		vec3( 0.04823, 0.01566, 0.83777 )
	);
	const mat3 ACESOutputMat = mat3(
		vec3(  1.60475, -0.10208, -0.00327 ),		vec3( -0.53108,  1.10813, -0.07276 ),
		vec3( -0.07367, -0.00605,  1.07602 )
	);
	color *= toneMappingExposure / 0.6;
	color = ACESInputMat * color;
	color = RRTAndODTFit( color );
	color = ACESOutputMat * color;
	return saturate( color );
}
const mat3 LINEAR_REC2020_TO_LINEAR_SRGB = mat3(
	vec3( 1.6605, - 0.1246, - 0.0182 ),
	vec3( - 0.5876, 1.1329, - 0.1006 ),
	vec3( - 0.0728, - 0.0083, 1.1187 )
);
const mat3 LINEAR_SRGB_TO_LINEAR_REC2020 = mat3(
	vec3( 0.6274, 0.0691, 0.0164 ),
	vec3( 0.3293, 0.9195, 0.0880 ),
	vec3( 0.0433, 0.0113, 0.8956 )
);
vec3 agxDefaultContrastApprox( vec3 x ) {
	vec3 x2 = x * x;
	vec3 x4 = x2 * x2;
	return + 15.5 * x4 * x2
		- 40.14 * x4 * x
		+ 31.96 * x4
		- 6.868 * x2 * x
		+ 0.4298 * x2
		+ 0.1191 * x
		- 0.00232;
}
vec3 AgXToneMapping( vec3 color ) {
	const mat3 AgXInsetMatrix = mat3(
		vec3( 0.856627153315983, 0.137318972929847, 0.11189821299995 ),
		vec3( 0.0951212405381588, 0.761241990602591, 0.0767994186031903 ),
		vec3( 0.0482516061458583, 0.101439036467562, 0.811302368396859 )
	);
	const mat3 AgXOutsetMatrix = mat3(
		vec3( 1.1271005818144368, - 0.1413297634984383, - 0.14132976349843826 ),
		vec3( - 0.11060664309660323, 1.157823702216272, - 0.11060664309660294 ),
		vec3( - 0.016493938717834573, - 0.016493938717834257, 1.2519364065950405 )
	);
	const float AgxMinEv = - 12.47393;	const float AgxMaxEv = 4.026069;
	color = LINEAR_SRGB_TO_LINEAR_REC2020 * color;
	color *= toneMappingExposure;
	color = AgXInsetMatrix * color;
	color = max( color, 1e-10 );	color = log2( color );
	color = ( color - AgxMinEv ) / ( AgxMaxEv - AgxMinEv );
	color = clamp( color, 0.0, 1.0 );
	color = agxDefaultContrastApprox( color );
	color = AgXOutsetMatrix * color;
	color = pow( max( vec3( 0.0 ), color ), vec3( 2.2 ) );
	color = LINEAR_REC2020_TO_LINEAR_SRGB * color;
	return color;
}
vec3 CustomToneMapping( vec3 color ) { return color; }`,_S=`#ifdef USE_TRANSMISSION
	material.transmission = transmission;
	material.transmissionAlpha = 1.0;
	material.thickness = thickness;
	material.attenuationDistance = attenuationDistance;
	material.attenuationColor = attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		material.transmission *= texture2D( transmissionMap, vTransmissionMapUv ).r;
	#endif
	#ifdef USE_THICKNESSMAP
		material.thickness *= texture2D( thicknessMap, vThicknessMapUv ).g;
	#endif
	vec3 pos = vWorldPosition;
	vec3 v = normalize( cameraPosition - pos );
	vec3 n = inverseTransformDirection( normal, viewMatrix );
	vec4 transmitted = getIBLVolumeRefraction(
		n, v, material.roughness, material.diffuseColor, material.specularColor, material.specularF90,
		pos, modelMatrix, viewMatrix, projectionMatrix, material.ior, material.thickness,
		material.attenuationColor, material.attenuationDistance );
	material.transmissionAlpha = mix( material.transmissionAlpha, transmitted.a, material.transmission );
	totalDiffuse = mix( totalDiffuse, transmitted.rgb, material.transmission );
#endif`,gS=`#ifdef USE_TRANSMISSION
	uniform float transmission;
	uniform float thickness;
	uniform float attenuationDistance;
	uniform vec3 attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		uniform sampler2D transmissionMap;
	#endif
	#ifdef USE_THICKNESSMAP
		uniform sampler2D thicknessMap;
	#endif
	uniform vec2 transmissionSamplerSize;
	uniform sampler2D transmissionSamplerMap;
	uniform mat4 modelMatrix;
	uniform mat4 projectionMatrix;
	varying vec3 vWorldPosition;
	float w0( float a ) {
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - a + 3.0 ) - 3.0 ) + 1.0 );
	}
	float w1( float a ) {
		return ( 1.0 / 6.0 ) * ( a *  a * ( 3.0 * a - 6.0 ) + 4.0 );
	}
	float w2( float a ){
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - 3.0 * a + 3.0 ) + 3.0 ) + 1.0 );
	}
	float w3( float a ) {
		return ( 1.0 / 6.0 ) * ( a * a * a );
	}
	float g0( float a ) {
		return w0( a ) + w1( a );
	}
	float g1( float a ) {
		return w2( a ) + w3( a );
	}
	float h0( float a ) {
		return - 1.0 + w1( a ) / ( w0( a ) + w1( a ) );
	}
	float h1( float a ) {
		return 1.0 + w3( a ) / ( w2( a ) + w3( a ) );
	}
	vec4 bicubic( sampler2D tex, vec2 uv, vec4 texelSize, float lod ) {
		uv = uv * texelSize.zw + 0.5;
		vec2 iuv = floor( uv );
		vec2 fuv = fract( uv );
		float g0x = g0( fuv.x );
		float g1x = g1( fuv.x );
		float h0x = h0( fuv.x );
		float h1x = h1( fuv.x );
		float h0y = h0( fuv.y );
		float h1y = h1( fuv.y );
		vec2 p0 = ( vec2( iuv.x + h0x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p1 = ( vec2( iuv.x + h1x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p2 = ( vec2( iuv.x + h0x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		vec2 p3 = ( vec2( iuv.x + h1x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		return g0( fuv.y ) * ( g0x * textureLod( tex, p0, lod ) + g1x * textureLod( tex, p1, lod ) ) +
			g1( fuv.y ) * ( g0x * textureLod( tex, p2, lod ) + g1x * textureLod( tex, p3, lod ) );
	}
	vec4 textureBicubic( sampler2D sampler, vec2 uv, float lod ) {
		vec2 fLodSize = vec2( textureSize( sampler, int( lod ) ) );
		vec2 cLodSize = vec2( textureSize( sampler, int( lod + 1.0 ) ) );
		vec2 fLodSizeInv = 1.0 / fLodSize;
		vec2 cLodSizeInv = 1.0 / cLodSize;
		vec4 fSample = bicubic( sampler, uv, vec4( fLodSizeInv, fLodSize ), floor( lod ) );
		vec4 cSample = bicubic( sampler, uv, vec4( cLodSizeInv, cLodSize ), ceil( lod ) );
		return mix( fSample, cSample, fract( lod ) );
	}
	vec3 getVolumeTransmissionRay( const in vec3 n, const in vec3 v, const in float thickness, const in float ior, const in mat4 modelMatrix ) {
		vec3 refractionVector = refract( - v, normalize( n ), 1.0 / ior );
		vec3 modelScale;
		modelScale.x = length( vec3( modelMatrix[ 0 ].xyz ) );
		modelScale.y = length( vec3( modelMatrix[ 1 ].xyz ) );
		modelScale.z = length( vec3( modelMatrix[ 2 ].xyz ) );
		return normalize( refractionVector ) * thickness * modelScale;
	}
	float applyIorToRoughness( const in float roughness, const in float ior ) {
		return roughness * clamp( ior * 2.0 - 2.0, 0.0, 1.0 );
	}
	vec4 getTransmissionSample( const in vec2 fragCoord, const in float roughness, const in float ior ) {
		float lod = log2( transmissionSamplerSize.x ) * applyIorToRoughness( roughness, ior );
		return textureBicubic( transmissionSamplerMap, fragCoord.xy, lod );
	}
	vec3 volumeAttenuation( const in float transmissionDistance, const in vec3 attenuationColor, const in float attenuationDistance ) {
		if ( isinf( attenuationDistance ) ) {
			return vec3( 1.0 );
		} else {
			vec3 attenuationCoefficient = -log( attenuationColor ) / attenuationDistance;
			vec3 transmittance = exp( - attenuationCoefficient * transmissionDistance );			return transmittance;
		}
	}
	vec4 getIBLVolumeRefraction( const in vec3 n, const in vec3 v, const in float roughness, const in vec3 diffuseColor,
		const in vec3 specularColor, const in float specularF90, const in vec3 position, const in mat4 modelMatrix,
		const in mat4 viewMatrix, const in mat4 projMatrix, const in float ior, const in float thickness,
		const in vec3 attenuationColor, const in float attenuationDistance ) {
		vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, ior, modelMatrix );
		vec3 refractedRayExit = position + transmissionRay;
		vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
		vec2 refractionCoords = ndcPos.xy / ndcPos.w;
		refractionCoords += 1.0;
		refractionCoords /= 2.0;
		vec4 transmittedLight = getTransmissionSample( refractionCoords, roughness, ior );
		vec3 transmittance = diffuseColor * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance );
		vec3 attenuatedColor = transmittance * transmittedLight.rgb;
		vec3 F = EnvironmentBRDF( n, v, specularColor, specularF90, roughness );
		float transmittanceFactor = ( transmittance.r + transmittance.g + transmittance.b ) / 3.0;
		return vec4( ( 1.0 - F ) * attenuatedColor, 1.0 - ( 1.0 - transmittedLight.a ) * transmittanceFactor );
	}
#endif`,vS=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_SPECULARMAP
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,xS=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	uniform mat3 mapTransform;
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	uniform mat3 alphaMapTransform;
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	uniform mat3 lightMapTransform;
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	uniform mat3 aoMapTransform;
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	uniform mat3 bumpMapTransform;
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	uniform mat3 normalMapTransform;
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_DISPLACEMENTMAP
	uniform mat3 displacementMapTransform;
	varying vec2 vDisplacementMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	uniform mat3 emissiveMapTransform;
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	uniform mat3 metalnessMapTransform;
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	uniform mat3 roughnessMapTransform;
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	uniform mat3 anisotropyMapTransform;
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	uniform mat3 clearcoatMapTransform;
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform mat3 clearcoatNormalMapTransform;
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform mat3 clearcoatRoughnessMapTransform;
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	uniform mat3 sheenColorMapTransform;
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	uniform mat3 sheenRoughnessMapTransform;
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	uniform mat3 iridescenceMapTransform;
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform mat3 iridescenceThicknessMapTransform;
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SPECULARMAP
	uniform mat3 specularMapTransform;
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	uniform mat3 specularColorMapTransform;
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	uniform mat3 specularIntensityMapTransform;
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,yS=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	vUv = vec3( uv, 1 ).xy;
#endif
#ifdef USE_MAP
	vMapUv = ( mapTransform * vec3( MAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ALPHAMAP
	vAlphaMapUv = ( alphaMapTransform * vec3( ALPHAMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_LIGHTMAP
	vLightMapUv = ( lightMapTransform * vec3( LIGHTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_AOMAP
	vAoMapUv = ( aoMapTransform * vec3( AOMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_BUMPMAP
	vBumpMapUv = ( bumpMapTransform * vec3( BUMPMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_NORMALMAP
	vNormalMapUv = ( normalMapTransform * vec3( NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_DISPLACEMENTMAP
	vDisplacementMapUv = ( displacementMapTransform * vec3( DISPLACEMENTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_EMISSIVEMAP
	vEmissiveMapUv = ( emissiveMapTransform * vec3( EMISSIVEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_METALNESSMAP
	vMetalnessMapUv = ( metalnessMapTransform * vec3( METALNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ROUGHNESSMAP
	vRoughnessMapUv = ( roughnessMapTransform * vec3( ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ANISOTROPYMAP
	vAnisotropyMapUv = ( anisotropyMapTransform * vec3( ANISOTROPYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOATMAP
	vClearcoatMapUv = ( clearcoatMapTransform * vec3( CLEARCOATMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	vClearcoatNormalMapUv = ( clearcoatNormalMapTransform * vec3( CLEARCOAT_NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	vClearcoatRoughnessMapUv = ( clearcoatRoughnessMapTransform * vec3( CLEARCOAT_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCEMAP
	vIridescenceMapUv = ( iridescenceMapTransform * vec3( IRIDESCENCEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	vIridescenceThicknessMapUv = ( iridescenceThicknessMapTransform * vec3( IRIDESCENCE_THICKNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_COLORMAP
	vSheenColorMapUv = ( sheenColorMapTransform * vec3( SHEEN_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	vSheenRoughnessMapUv = ( sheenRoughnessMapTransform * vec3( SHEEN_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULARMAP
	vSpecularMapUv = ( specularMapTransform * vec3( SPECULARMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_COLORMAP
	vSpecularColorMapUv = ( specularColorMapTransform * vec3( SPECULAR_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	vSpecularIntensityMapUv = ( specularIntensityMapTransform * vec3( SPECULAR_INTENSITYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_TRANSMISSIONMAP
	vTransmissionMapUv = ( transmissionMapTransform * vec3( TRANSMISSIONMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_THICKNESSMAP
	vThicknessMapUv = ( thicknessMapTransform * vec3( THICKNESSMAP_UV, 1 ) ).xy;
#endif`,SS=`#if defined( USE_ENVMAP ) || defined( DISTANCE ) || defined ( USE_SHADOWMAP ) || defined ( USE_TRANSMISSION ) || NUM_SPOT_LIGHT_COORDS > 0
	vec4 worldPosition = vec4( transformed, 1.0 );
	#ifdef USE_BATCHING
		worldPosition = batchingMatrix * worldPosition;
	#endif
	#ifdef USE_INSTANCING
		worldPosition = instanceMatrix * worldPosition;
	#endif
	worldPosition = modelMatrix * worldPosition;
#endif`;const MS=`varying vec2 vUv;
uniform mat3 uvTransform;
void main() {
	vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	gl_Position = vec4( position.xy, 1.0, 1.0 );
}`,ES=`uniform sampler2D t2D;
uniform float backgroundIntensity;
varying vec2 vUv;
void main() {
	vec4 texColor = texture2D( t2D, vUv );
	#ifdef DECODE_VIDEO_TEXTURE
		texColor = vec4( mix( pow( texColor.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), texColor.rgb * 0.0773993808, vec3( lessThanEqual( texColor.rgb, vec3( 0.04045 ) ) ) ), texColor.w );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,bS=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,TS=`#ifdef ENVMAP_TYPE_CUBE
	uniform samplerCube envMap;
#elif defined( ENVMAP_TYPE_CUBE_UV )
	uniform sampler2D envMap;
#endif
uniform float flipEnvMap;
uniform float backgroundBlurriness;
uniform float backgroundIntensity;
varying vec3 vWorldDirection;
#include <cube_uv_reflection_fragment>
void main() {
	#ifdef ENVMAP_TYPE_CUBE
		vec4 texColor = textureCube( envMap, vec3( flipEnvMap * vWorldDirection.x, vWorldDirection.yz ) );
	#elif defined( ENVMAP_TYPE_CUBE_UV )
		vec4 texColor = textureCubeUV( envMap, vWorldDirection, backgroundBlurriness );
	#else
		vec4 texColor = vec4( 0.0, 0.0, 0.0, 1.0 );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,AS=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,wS=`uniform samplerCube tCube;
uniform float tFlip;
uniform float opacity;
varying vec3 vWorldDirection;
void main() {
	vec4 texColor = textureCube( tCube, vec3( tFlip * vWorldDirection.x, vWorldDirection.yz ) );
	gl_FragColor = texColor;
	gl_FragColor.a *= opacity;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,RS=`#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
varying vec2 vHighPrecisionZW;
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vHighPrecisionZW = gl_Position.zw;
}`,CS=`#if DEPTH_PACKING == 3200
	uniform float opacity;
#endif
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
varying vec2 vHighPrecisionZW;
void main() {
	#include <clipping_planes_fragment>
	vec4 diffuseColor = vec4( 1.0 );
	#if DEPTH_PACKING == 3200
		diffuseColor.a = opacity;
	#endif
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <logdepthbuf_fragment>
	float fragCoordZ = 0.5 * vHighPrecisionZW[0] / vHighPrecisionZW[1] + 0.5;
	#if DEPTH_PACKING == 3200
		gl_FragColor = vec4( vec3( 1.0 - fragCoordZ ), opacity );
	#elif DEPTH_PACKING == 3201
		gl_FragColor = packDepthToRGBA( fragCoordZ );
	#endif
}`,PS=`#define DISTANCE
varying vec3 vWorldPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <worldpos_vertex>
	#include <clipping_planes_vertex>
	vWorldPosition = worldPosition.xyz;
}`,LS=`#define DISTANCE
uniform vec3 referencePosition;
uniform float nearDistance;
uniform float farDistance;
varying vec3 vWorldPosition;
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <clipping_planes_pars_fragment>
void main () {
	#include <clipping_planes_fragment>
	vec4 diffuseColor = vec4( 1.0 );
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	float dist = length( vWorldPosition - referencePosition );
	dist = ( dist - nearDistance ) / ( farDistance - nearDistance );
	dist = saturate( dist );
	gl_FragColor = packDepthToRGBA( dist );
}`,DS=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
}`,US=`uniform sampler2D tEquirect;
varying vec3 vWorldDirection;
#include <common>
void main() {
	vec3 direction = normalize( vWorldDirection );
	vec2 sampleUV = equirectUv( direction );
	gl_FragColor = texture2D( tEquirect, sampleUV );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,IS=`uniform float scale;
attribute float lineDistance;
varying float vLineDistance;
#include <common>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	vLineDistance = scale * lineDistance;
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,OS=`uniform vec3 diffuse;
uniform float opacity;
uniform float dashSize;
uniform float totalSize;
varying float vLineDistance;
#include <common>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	#include <clipping_planes_fragment>
	if ( mod( vLineDistance, totalSize ) > dashSize ) {
		discard;
	}
	vec3 outgoingLight = vec3( 0.0 );
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,NS=`#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#if defined ( USE_ENVMAP ) || defined ( USE_SKINNING )
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinbase_vertex>
		#include <skinnormal_vertex>
		#include <defaultnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <fog_vertex>
}`,FS=`uniform vec3 diffuse;
uniform float opacity;
#ifndef FLAT_SHADED
	varying vec3 vNormal;
#endif
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	#include <clipping_planes_fragment>
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		reflectedLight.indirectDiffuse += lightMapTexel.rgb * lightMapIntensity * RECIPROCAL_PI;
	#else
		reflectedLight.indirectDiffuse += vec3( 1.0 );
	#endif
	#include <aomap_fragment>
	reflectedLight.indirectDiffuse *= diffuseColor.rgb;
	vec3 outgoingLight = reflectedLight.indirectDiffuse;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,zS=`#define LAMBERT
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,BS=`#define LAMBERT
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_lambert_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	#include <clipping_planes_fragment>
	vec4 diffuseColor = vec4( diffuse, opacity );
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_lambert_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,kS=`#define MATCAP
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <displacementmap_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
	vViewPosition = - mvPosition.xyz;
}`,VS=`#define MATCAP
uniform vec3 diffuse;
uniform float opacity;
uniform sampler2D matcap;
varying vec3 vViewPosition;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	#include <clipping_planes_fragment>
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	vec3 viewDir = normalize( vViewPosition );
	vec3 x = normalize( vec3( viewDir.z, 0.0, - viewDir.x ) );
	vec3 y = cross( viewDir, x );
	vec2 uv = vec2( dot( x, normal ), dot( y, normal ) ) * 0.495 + 0.5;
	#ifdef USE_MATCAP
		vec4 matcapColor = texture2D( matcap, uv );
	#else
		vec4 matcapColor = vec4( vec3( mix( 0.2, 0.8, uv.y ) ), 1.0 );
	#endif
	vec3 outgoingLight = diffuseColor.rgb * matcapColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,HS=`#define NORMAL
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	vViewPosition = - mvPosition.xyz;
#endif
}`,GS=`#define NORMAL
uniform float opacity;
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <packing>
#include <uv_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	gl_FragColor = vec4( packNormalToRGB( normal ), opacity );
	#ifdef OPAQUE
		gl_FragColor.a = 1.0;
	#endif
}`,WS=`#define PHONG
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,XS=`#define PHONG
uniform vec3 diffuse;
uniform vec3 emissive;
uniform vec3 specular;
uniform float shininess;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_phong_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	#include <clipping_planes_fragment>
	vec4 diffuseColor = vec4( diffuse, opacity );
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_phong_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + reflectedLight.directSpecular + reflectedLight.indirectSpecular + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,qS=`#define STANDARD
varying vec3 vViewPosition;
#ifdef USE_TRANSMISSION
	varying vec3 vWorldPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
#ifdef USE_TRANSMISSION
	vWorldPosition = worldPosition.xyz;
#endif
}`,YS=`#define STANDARD
#ifdef PHYSICAL
	#define IOR
	#define USE_SPECULAR
#endif
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float roughness;
uniform float metalness;
uniform float opacity;
#ifdef IOR
	uniform float ior;
#endif
#ifdef USE_SPECULAR
	uniform float specularIntensity;
	uniform vec3 specularColor;
	#ifdef USE_SPECULAR_COLORMAP
		uniform sampler2D specularColorMap;
	#endif
	#ifdef USE_SPECULAR_INTENSITYMAP
		uniform sampler2D specularIntensityMap;
	#endif
#endif
#ifdef USE_CLEARCOAT
	uniform float clearcoat;
	uniform float clearcoatRoughness;
#endif
#ifdef USE_IRIDESCENCE
	uniform float iridescence;
	uniform float iridescenceIOR;
	uniform float iridescenceThicknessMinimum;
	uniform float iridescenceThicknessMaximum;
#endif
#ifdef USE_SHEEN
	uniform vec3 sheenColor;
	uniform float sheenRoughness;
	#ifdef USE_SHEEN_COLORMAP
		uniform sampler2D sheenColorMap;
	#endif
	#ifdef USE_SHEEN_ROUGHNESSMAP
		uniform sampler2D sheenRoughnessMap;
	#endif
#endif
#ifdef USE_ANISOTROPY
	uniform vec2 anisotropyVector;
	#ifdef USE_ANISOTROPYMAP
		uniform sampler2D anisotropyMap;
	#endif
#endif
varying vec3 vViewPosition;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <iridescence_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_physical_pars_fragment>
#include <transmission_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <clearcoat_pars_fragment>
#include <iridescence_pars_fragment>
#include <roughnessmap_pars_fragment>
#include <metalnessmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	#include <clipping_planes_fragment>
	vec4 diffuseColor = vec4( diffuse, opacity );
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <roughnessmap_fragment>
	#include <metalnessmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <clearcoat_normal_fragment_begin>
	#include <clearcoat_normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_physical_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 totalDiffuse = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse;
	vec3 totalSpecular = reflectedLight.directSpecular + reflectedLight.indirectSpecular;
	#include <transmission_fragment>
	vec3 outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance;
	#ifdef USE_SHEEN
		float sheenEnergyComp = 1.0 - 0.157 * max3( material.sheenColor );
		outgoingLight = outgoingLight * sheenEnergyComp + sheenSpecularDirect + sheenSpecularIndirect;
	#endif
	#ifdef USE_CLEARCOAT
		float dotNVcc = saturate( dot( geometryClearcoatNormal, geometryViewDir ) );
		vec3 Fcc = F_Schlick( material.clearcoatF0, material.clearcoatF90, dotNVcc );
		outgoingLight = outgoingLight * ( 1.0 - material.clearcoat * Fcc ) + ( clearcoatSpecularDirect + clearcoatSpecularIndirect ) * material.clearcoat;
	#endif
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,$S=`#define TOON
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,jS=`#define TOON
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <gradientmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_toon_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	#include <clipping_planes_fragment>
	vec4 diffuseColor = vec4( diffuse, opacity );
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_toon_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,KS=`uniform float size;
uniform float scale;
#include <common>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
#ifdef USE_POINTS_UV
	varying vec2 vUv;
	uniform mat3 uvTransform;
#endif
void main() {
	#ifdef USE_POINTS_UV
		vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	#endif
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	gl_PointSize = size;
	#ifdef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) gl_PointSize *= ( scale / - mvPosition.z );
	#endif
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <fog_vertex>
}`,ZS=`uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <color_pars_fragment>
#include <map_particle_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <logdepthbuf_fragment>
	#include <map_particle_fragment>
	#include <color_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,JS=`#include <common>
#include <batching_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <shadowmap_pars_vertex>
void main() {
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,QS=`uniform vec3 color;
uniform float opacity;
#include <common>
#include <packing>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <logdepthbuf_pars_fragment>
#include <shadowmap_pars_fragment>
#include <shadowmask_pars_fragment>
void main() {
	#include <logdepthbuf_fragment>
	gl_FragColor = vec4( color, opacity * ( 1.0 - getShadowMask() ) );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`,eM=`uniform float rotation;
uniform vec2 center;
#include <common>
#include <uv_pars_vertex>
#include <fog_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	vec4 mvPosition = modelViewMatrix * vec4( 0.0, 0.0, 0.0, 1.0 );
	vec2 scale;
	scale.x = length( vec3( modelMatrix[ 0 ].x, modelMatrix[ 0 ].y, modelMatrix[ 0 ].z ) );
	scale.y = length( vec3( modelMatrix[ 1 ].x, modelMatrix[ 1 ].y, modelMatrix[ 1 ].z ) );
	#ifndef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) scale *= - mvPosition.z;
	#endif
	vec2 alignedPosition = ( position.xy - ( center - vec2( 0.5 ) ) ) * scale;
	vec2 rotatedPosition;
	rotatedPosition.x = cos( rotation ) * alignedPosition.x - sin( rotation ) * alignedPosition.y;
	rotatedPosition.y = sin( rotation ) * alignedPosition.x + cos( rotation ) * alignedPosition.y;
	mvPosition.xy += rotatedPosition;
	gl_Position = projectionMatrix * mvPosition;
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,tM=`uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`,Xe={alphahash_fragment:Ex,alphahash_pars_fragment:bx,alphamap_fragment:Tx,alphamap_pars_fragment:Ax,alphatest_fragment:wx,alphatest_pars_fragment:Rx,aomap_fragment:Cx,aomap_pars_fragment:Px,batching_pars_vertex:Lx,batching_vertex:Dx,begin_vertex:Ux,beginnormal_vertex:Ix,bsdfs:Ox,iridescence_fragment:Nx,bumpmap_pars_fragment:Fx,clipping_planes_fragment:zx,clipping_planes_pars_fragment:Bx,clipping_planes_pars_vertex:kx,clipping_planes_vertex:Vx,color_fragment:Hx,color_pars_fragment:Gx,color_pars_vertex:Wx,color_vertex:Xx,common:qx,cube_uv_reflection_fragment:Yx,defaultnormal_vertex:$x,displacementmap_pars_vertex:jx,displacementmap_vertex:Kx,emissivemap_fragment:Zx,emissivemap_pars_fragment:Jx,colorspace_fragment:Qx,colorspace_pars_fragment:ey,envmap_fragment:ty,envmap_common_pars_fragment:ny,envmap_pars_fragment:iy,envmap_pars_vertex:sy,envmap_physical_pars_fragment:_y,envmap_vertex:ry,fog_vertex:oy,fog_pars_vertex:ay,fog_fragment:ly,fog_pars_fragment:cy,gradientmap_pars_fragment:uy,lightmap_fragment:fy,lightmap_pars_fragment:hy,lights_lambert_fragment:dy,lights_lambert_pars_fragment:py,lights_pars_begin:my,lights_toon_fragment:gy,lights_toon_pars_fragment:vy,lights_phong_fragment:xy,lights_phong_pars_fragment:yy,lights_physical_fragment:Sy,lights_physical_pars_fragment:My,lights_fragment_begin:Ey,lights_fragment_maps:by,lights_fragment_end:Ty,logdepthbuf_fragment:Ay,logdepthbuf_pars_fragment:wy,logdepthbuf_pars_vertex:Ry,logdepthbuf_vertex:Cy,map_fragment:Py,map_pars_fragment:Ly,map_particle_fragment:Dy,map_particle_pars_fragment:Uy,metalnessmap_fragment:Iy,metalnessmap_pars_fragment:Oy,morphcolor_vertex:Ny,morphnormal_vertex:Fy,morphtarget_pars_vertex:zy,morphtarget_vertex:By,normal_fragment_begin:ky,normal_fragment_maps:Vy,normal_pars_fragment:Hy,normal_pars_vertex:Gy,normal_vertex:Wy,normalmap_pars_fragment:Xy,clearcoat_normal_fragment_begin:qy,clearcoat_normal_fragment_maps:Yy,clearcoat_pars_fragment:$y,iridescence_pars_fragment:jy,opaque_fragment:Ky,packing:Zy,premultiplied_alpha_fragment:Jy,project_vertex:Qy,dithering_fragment:eS,dithering_pars_fragment:tS,roughnessmap_fragment:nS,roughnessmap_pars_fragment:iS,shadowmap_pars_fragment:sS,shadowmap_pars_vertex:rS,shadowmap_vertex:oS,shadowmask_pars_fragment:aS,skinbase_vertex:lS,skinning_pars_vertex:cS,skinning_vertex:uS,skinnormal_vertex:fS,specularmap_fragment:hS,specularmap_pars_fragment:dS,tonemapping_fragment:pS,tonemapping_pars_fragment:mS,transmission_fragment:_S,transmission_pars_fragment:gS,uv_pars_fragment:vS,uv_pars_vertex:xS,uv_vertex:yS,worldpos_vertex:SS,background_vert:MS,background_frag:ES,backgroundCube_vert:bS,backgroundCube_frag:TS,cube_vert:AS,cube_frag:wS,depth_vert:RS,depth_frag:CS,distanceRGBA_vert:PS,distanceRGBA_frag:LS,equirect_vert:DS,equirect_frag:US,linedashed_vert:IS,linedashed_frag:OS,meshbasic_vert:NS,meshbasic_frag:FS,meshlambert_vert:zS,meshlambert_frag:BS,meshmatcap_vert:kS,meshmatcap_frag:VS,meshnormal_vert:HS,meshnormal_frag:GS,meshphong_vert:WS,meshphong_frag:XS,meshphysical_vert:qS,meshphysical_frag:YS,meshtoon_vert:$S,meshtoon_frag:jS,points_vert:KS,points_frag:ZS,shadow_vert:JS,shadow_frag:QS,sprite_vert:eM,sprite_frag:tM},ve={common:{diffuse:{value:new Qe(16777215)},opacity:{value:1},map:{value:null},mapTransform:{value:new je},alphaMap:{value:null},alphaMapTransform:{value:new je},alphaTest:{value:0}},specularmap:{specularMap:{value:null},specularMapTransform:{value:new je}},envmap:{envMap:{value:null},flipEnvMap:{value:-1},reflectivity:{value:1},ior:{value:1.5},refractionRatio:{value:.98}},aomap:{aoMap:{value:null},aoMapIntensity:{value:1},aoMapTransform:{value:new je}},lightmap:{lightMap:{value:null},lightMapIntensity:{value:1},lightMapTransform:{value:new je}},bumpmap:{bumpMap:{value:null},bumpMapTransform:{value:new je},bumpScale:{value:1}},normalmap:{normalMap:{value:null},normalMapTransform:{value:new je},normalScale:{value:new He(1,1)}},displacementmap:{displacementMap:{value:null},displacementMapTransform:{value:new je},displacementScale:{value:1},displacementBias:{value:0}},emissivemap:{emissiveMap:{value:null},emissiveMapTransform:{value:new je}},metalnessmap:{metalnessMap:{value:null},metalnessMapTransform:{value:new je}},roughnessmap:{roughnessMap:{value:null},roughnessMapTransform:{value:new je}},gradientmap:{gradientMap:{value:null}},fog:{fogDensity:{value:25e-5},fogNear:{value:1},fogFar:{value:2e3},fogColor:{value:new Qe(16777215)}},lights:{ambientLightColor:{value:[]},lightProbe:{value:[]},directionalLights:{value:[],properties:{direction:{},color:{}}},directionalLightShadows:{value:[],properties:{shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},directionalShadowMap:{value:[]},directionalShadowMatrix:{value:[]},spotLights:{value:[],properties:{color:{},position:{},direction:{},distance:{},coneCos:{},penumbraCos:{},decay:{}}},spotLightShadows:{value:[],properties:{shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},spotLightMap:{value:[]},spotShadowMap:{value:[]},spotLightMatrix:{value:[]},pointLights:{value:[],properties:{color:{},position:{},decay:{},distance:{}}},pointLightShadows:{value:[],properties:{shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{},shadowCameraNear:{},shadowCameraFar:{}}},pointShadowMap:{value:[]},pointShadowMatrix:{value:[]},hemisphereLights:{value:[],properties:{direction:{},skyColor:{},groundColor:{}}},rectAreaLights:{value:[],properties:{color:{},position:{},width:{},height:{}}},ltc_1:{value:null},ltc_2:{value:null}},points:{diffuse:{value:new Qe(16777215)},opacity:{value:1},size:{value:1},scale:{value:1},map:{value:null},alphaMap:{value:null},alphaMapTransform:{value:new je},alphaTest:{value:0},uvTransform:{value:new je}},sprite:{diffuse:{value:new Qe(16777215)},opacity:{value:1},center:{value:new He(.5,.5)},rotation:{value:0},map:{value:null},mapTransform:{value:new je},alphaMap:{value:null},alphaMapTransform:{value:new je},alphaTest:{value:0}}},ti={basic:{uniforms:Qt([ve.common,ve.specularmap,ve.envmap,ve.aomap,ve.lightmap,ve.fog]),vertexShader:Xe.meshbasic_vert,fragmentShader:Xe.meshbasic_frag},lambert:{uniforms:Qt([ve.common,ve.specularmap,ve.envmap,ve.aomap,ve.lightmap,ve.emissivemap,ve.bumpmap,ve.normalmap,ve.displacementmap,ve.fog,ve.lights,{emissive:{value:new Qe(0)}}]),vertexShader:Xe.meshlambert_vert,fragmentShader:Xe.meshlambert_frag},phong:{uniforms:Qt([ve.common,ve.specularmap,ve.envmap,ve.aomap,ve.lightmap,ve.emissivemap,ve.bumpmap,ve.normalmap,ve.displacementmap,ve.fog,ve.lights,{emissive:{value:new Qe(0)},specular:{value:new Qe(1118481)},shininess:{value:30}}]),vertexShader:Xe.meshphong_vert,fragmentShader:Xe.meshphong_frag},standard:{uniforms:Qt([ve.common,ve.envmap,ve.aomap,ve.lightmap,ve.emissivemap,ve.bumpmap,ve.normalmap,ve.displacementmap,ve.roughnessmap,ve.metalnessmap,ve.fog,ve.lights,{emissive:{value:new Qe(0)},roughness:{value:1},metalness:{value:0},envMapIntensity:{value:1}}]),vertexShader:Xe.meshphysical_vert,fragmentShader:Xe.meshphysical_frag},toon:{uniforms:Qt([ve.common,ve.aomap,ve.lightmap,ve.emissivemap,ve.bumpmap,ve.normalmap,ve.displacementmap,ve.gradientmap,ve.fog,ve.lights,{emissive:{value:new Qe(0)}}]),vertexShader:Xe.meshtoon_vert,fragmentShader:Xe.meshtoon_frag},matcap:{uniforms:Qt([ve.common,ve.bumpmap,ve.normalmap,ve.displacementmap,ve.fog,{matcap:{value:null}}]),vertexShader:Xe.meshmatcap_vert,fragmentShader:Xe.meshmatcap_frag},points:{uniforms:Qt([ve.points,ve.fog]),vertexShader:Xe.points_vert,fragmentShader:Xe.points_frag},dashed:{uniforms:Qt([ve.common,ve.fog,{scale:{value:1},dashSize:{value:1},totalSize:{value:2}}]),vertexShader:Xe.linedashed_vert,fragmentShader:Xe.linedashed_frag},depth:{uniforms:Qt([ve.common,ve.displacementmap]),vertexShader:Xe.depth_vert,fragmentShader:Xe.depth_frag},normal:{uniforms:Qt([ve.common,ve.bumpmap,ve.normalmap,ve.displacementmap,{opacity:{value:1}}]),vertexShader:Xe.meshnormal_vert,fragmentShader:Xe.meshnormal_frag},sprite:{uniforms:Qt([ve.sprite,ve.fog]),vertexShader:Xe.sprite_vert,fragmentShader:Xe.sprite_frag},background:{uniforms:{uvTransform:{value:new je},t2D:{value:null},backgroundIntensity:{value:1}},vertexShader:Xe.background_vert,fragmentShader:Xe.background_frag},backgroundCube:{uniforms:{envMap:{value:null},flipEnvMap:{value:-1},backgroundBlurriness:{value:0},backgroundIntensity:{value:1}},vertexShader:Xe.backgroundCube_vert,fragmentShader:Xe.backgroundCube_frag},cube:{uniforms:{tCube:{value:null},tFlip:{value:-1},opacity:{value:1}},vertexShader:Xe.cube_vert,fragmentShader:Xe.cube_frag},equirect:{uniforms:{tEquirect:{value:null}},vertexShader:Xe.equirect_vert,fragmentShader:Xe.equirect_frag},distanceRGBA:{uniforms:Qt([ve.common,ve.displacementmap,{referencePosition:{value:new $},nearDistance:{value:1},farDistance:{value:1e3}}]),vertexShader:Xe.distanceRGBA_vert,fragmentShader:Xe.distanceRGBA_frag},shadow:{uniforms:Qt([ve.lights,ve.fog,{color:{value:new Qe(0)},opacity:{value:1}}]),vertexShader:Xe.shadow_vert,fragmentShader:Xe.shadow_frag}};ti.physical={uniforms:Qt([ti.standard.uniforms,{clearcoat:{value:0},clearcoatMap:{value:null},clearcoatMapTransform:{value:new je},clearcoatNormalMap:{value:null},clearcoatNormalMapTransform:{value:new je},clearcoatNormalScale:{value:new He(1,1)},clearcoatRoughness:{value:0},clearcoatRoughnessMap:{value:null},clearcoatRoughnessMapTransform:{value:new je},iridescence:{value:0},iridescenceMap:{value:null},iridescenceMapTransform:{value:new je},iridescenceIOR:{value:1.3},iridescenceThicknessMinimum:{value:100},iridescenceThicknessMaximum:{value:400},iridescenceThicknessMap:{value:null},iridescenceThicknessMapTransform:{value:new je},sheen:{value:0},sheenColor:{value:new Qe(0)},sheenColorMap:{value:null},sheenColorMapTransform:{value:new je},sheenRoughness:{value:1},sheenRoughnessMap:{value:null},sheenRoughnessMapTransform:{value:new je},transmission:{value:0},transmissionMap:{value:null},transmissionMapTransform:{value:new je},transmissionSamplerSize:{value:new He},transmissionSamplerMap:{value:null},thickness:{value:0},thicknessMap:{value:null},thicknessMapTransform:{value:new je},attenuationDistance:{value:0},attenuationColor:{value:new Qe(0)},specularColor:{value:new Qe(1,1,1)},specularColorMap:{value:null},specularColorMapTransform:{value:new je},specularIntensity:{value:1},specularIntensityMap:{value:null},specularIntensityMapTransform:{value:new je},anisotropyVector:{value:new He},anisotropyMap:{value:null},anisotropyMapTransform:{value:new je}}]),vertexShader:Xe.meshphysical_vert,fragmentShader:Xe.meshphysical_frag};const ha={r:0,b:0,g:0};function nM(i,e,t,n,s,r,o){const a=new Qe(0);let l=r===!0?0:1,c,u,f=null,h=0,d=null;function g(m,p){let x=!1,y=p.isScene===!0?p.background:null;y&&y.isTexture&&(y=(p.backgroundBlurriness>0?t:e).get(y)),y===null?_(a,l):y&&y.isColor&&(_(y,1),x=!0);const S=i.xr.getEnvironmentBlendMode();S==="additive"?n.buffers.color.setClear(0,0,0,1,o):S==="alpha-blend"&&n.buffers.color.setClear(0,0,0,0,o),(i.autoClear||x)&&i.clear(i.autoClearColor,i.autoClearDepth,i.autoClearStencil),y&&(y.isCubeTexture||y.mapping===pl)?(u===void 0&&(u=new Yi(new Fo(1,1,1),new rs({name:"BackgroundCubeMaterial",uniforms:Lr(ti.backgroundCube.uniforms),vertexShader:ti.backgroundCube.vertexShader,fragmentShader:ti.backgroundCube.fragmentShader,side:un,depthTest:!1,depthWrite:!1,fog:!1})),u.geometry.deleteAttribute("normal"),u.geometry.deleteAttribute("uv"),u.onBeforeRender=function(R,L,w){this.matrixWorld.copyPosition(w.matrixWorld)},Object.defineProperty(u.material,"envMap",{get:function(){return this.uniforms.envMap.value}}),s.update(u)),u.material.uniforms.envMap.value=y,u.material.uniforms.flipEnvMap.value=y.isCubeTexture&&y.isRenderTargetTexture===!1?-1:1,u.material.uniforms.backgroundBlurriness.value=p.backgroundBlurriness,u.material.uniforms.backgroundIntensity.value=p.backgroundIntensity,u.material.toneMapped=at.getTransfer(y.colorSpace)!==mt,(f!==y||h!==y.version||d!==i.toneMapping)&&(u.material.needsUpdate=!0,f=y,h=y.version,d=i.toneMapping),u.layers.enableAll(),m.unshift(u,u.geometry,u.material,0,0,null)):y&&y.isTexture&&(c===void 0&&(c=new Yi(new Cu(2,2),new rs({name:"BackgroundMaterial",uniforms:Lr(ti.background.uniforms),vertexShader:ti.background.vertexShader,fragmentShader:ti.background.fragmentShader,side:ss,depthTest:!1,depthWrite:!1,fog:!1})),c.geometry.deleteAttribute("normal"),Object.defineProperty(c.material,"map",{get:function(){return this.uniforms.t2D.value}}),s.update(c)),c.material.uniforms.t2D.value=y,c.material.uniforms.backgroundIntensity.value=p.backgroundIntensity,c.material.toneMapped=at.getTransfer(y.colorSpace)!==mt,y.matrixAutoUpdate===!0&&y.updateMatrix(),c.material.uniforms.uvTransform.value.copy(y.matrix),(f!==y||h!==y.version||d!==i.toneMapping)&&(c.material.needsUpdate=!0,f=y,h=y.version,d=i.toneMapping),c.layers.enableAll(),m.unshift(c,c.geometry,c.material,0,0,null))}function _(m,p){m.getRGB(ha,rm(i)),n.buffers.color.setClear(ha.r,ha.g,ha.b,p,o)}return{getClearColor:function(){return a},setClearColor:function(m,p=1){a.set(m),l=p,_(a,l)},getClearAlpha:function(){return l},setClearAlpha:function(m){l=m,_(a,l)},render:g}}function iM(i,e,t,n){const s=i.getParameter(i.MAX_VERTEX_ATTRIBS),r=n.isWebGL2?null:e.get("OES_vertex_array_object"),o=n.isWebGL2||r!==null,a={},l=m(null);let c=l,u=!1;function f(O,k,H,q,Z){let W=!1;if(o){const j=_(q,H,k);c!==j&&(c=j,d(c.object)),W=p(O,q,H,Z),W&&x(O,q,H,Z)}else{const j=k.wireframe===!0;(c.geometry!==q.id||c.program!==H.id||c.wireframe!==j)&&(c.geometry=q.id,c.program=H.id,c.wireframe=j,W=!0)}Z!==null&&t.update(Z,i.ELEMENT_ARRAY_BUFFER),(W||u)&&(u=!1,B(O,k,H,q),Z!==null&&i.bindBuffer(i.ELEMENT_ARRAY_BUFFER,t.get(Z).buffer))}function h(){return n.isWebGL2?i.createVertexArray():r.createVertexArrayOES()}function d(O){return n.isWebGL2?i.bindVertexArray(O):r.bindVertexArrayOES(O)}function g(O){return n.isWebGL2?i.deleteVertexArray(O):r.deleteVertexArrayOES(O)}function _(O,k,H){const q=H.wireframe===!0;let Z=a[O.id];Z===void 0&&(Z={},a[O.id]=Z);let W=Z[k.id];W===void 0&&(W={},Z[k.id]=W);let j=W[q];return j===void 0&&(j=m(h()),W[q]=j),j}function m(O){const k=[],H=[],q=[];for(let Z=0;Z<s;Z++)k[Z]=0,H[Z]=0,q[Z]=0;return{geometry:null,program:null,wireframe:!1,newAttributes:k,enabledAttributes:H,attributeDivisors:q,object:O,attributes:{},index:null}}function p(O,k,H,q){const Z=c.attributes,W=k.attributes;let j=0;const G=H.getAttributes();for(const re in G)if(G[re].location>=0){const le=Z[re];let _e=W[re];if(_e===void 0&&(re==="instanceMatrix"&&O.instanceMatrix&&(_e=O.instanceMatrix),re==="instanceColor"&&O.instanceColor&&(_e=O.instanceColor)),le===void 0||le.attribute!==_e||_e&&le.data!==_e.data)return!0;j++}return c.attributesNum!==j||c.index!==q}function x(O,k,H,q){const Z={},W=k.attributes;let j=0;const G=H.getAttributes();for(const re in G)if(G[re].location>=0){let le=W[re];le===void 0&&(re==="instanceMatrix"&&O.instanceMatrix&&(le=O.instanceMatrix),re==="instanceColor"&&O.instanceColor&&(le=O.instanceColor));const _e={};_e.attribute=le,le&&le.data&&(_e.data=le.data),Z[re]=_e,j++}c.attributes=Z,c.attributesNum=j,c.index=q}function y(){const O=c.newAttributes;for(let k=0,H=O.length;k<H;k++)O[k]=0}function S(O){R(O,0)}function R(O,k){const H=c.newAttributes,q=c.enabledAttributes,Z=c.attributeDivisors;H[O]=1,q[O]===0&&(i.enableVertexAttribArray(O),q[O]=1),Z[O]!==k&&((n.isWebGL2?i:e.get("ANGLE_instanced_arrays"))[n.isWebGL2?"vertexAttribDivisor":"vertexAttribDivisorANGLE"](O,k),Z[O]=k)}function L(){const O=c.newAttributes,k=c.enabledAttributes;for(let H=0,q=k.length;H<q;H++)k[H]!==O[H]&&(i.disableVertexAttribArray(H),k[H]=0)}function w(O,k,H,q,Z,W,j){j===!0?i.vertexAttribIPointer(O,k,H,Z,W):i.vertexAttribPointer(O,k,H,q,Z,W)}function B(O,k,H,q){if(n.isWebGL2===!1&&(O.isInstancedMesh||q.isInstancedBufferGeometry)&&e.get("ANGLE_instanced_arrays")===null)return;y();const Z=q.attributes,W=H.getAttributes(),j=k.defaultAttributeValues;for(const G in W){const re=W[G];if(re.location>=0){let Q=Z[G];if(Q===void 0&&(G==="instanceMatrix"&&O.instanceMatrix&&(Q=O.instanceMatrix),G==="instanceColor"&&O.instanceColor&&(Q=O.instanceColor)),Q!==void 0){const le=Q.normalized,_e=Q.itemSize,be=t.get(Q);if(be===void 0)continue;const Te=be.buffer,Ue=be.type,Ie=be.bytesPerElement,Se=n.isWebGL2===!0&&(Ue===i.INT||Ue===i.UNSIGNED_INT||Q.gpuType===Hp);if(Q.isInterleavedBufferAttribute){const Ke=Q.data,E=Ke.stride,z=Q.offset;if(Ke.isInstancedInterleavedBuffer){for(let V=0;V<re.locationSize;V++)R(re.location+V,Ke.meshPerAttribute);O.isInstancedMesh!==!0&&q._maxInstanceCount===void 0&&(q._maxInstanceCount=Ke.meshPerAttribute*Ke.count)}else for(let V=0;V<re.locationSize;V++)S(re.location+V);i.bindBuffer(i.ARRAY_BUFFER,Te);for(let V=0;V<re.locationSize;V++)w(re.location+V,_e/re.locationSize,Ue,le,E*Ie,(z+_e/re.locationSize*V)*Ie,Se)}else{if(Q.isInstancedBufferAttribute){for(let Ke=0;Ke<re.locationSize;Ke++)R(re.location+Ke,Q.meshPerAttribute);O.isInstancedMesh!==!0&&q._maxInstanceCount===void 0&&(q._maxInstanceCount=Q.meshPerAttribute*Q.count)}else for(let Ke=0;Ke<re.locationSize;Ke++)S(re.location+Ke);i.bindBuffer(i.ARRAY_BUFFER,Te);for(let Ke=0;Ke<re.locationSize;Ke++)w(re.location+Ke,_e/re.locationSize,Ue,le,_e*Ie,_e/re.locationSize*Ke*Ie,Se)}}else if(j!==void 0){const le=j[G];if(le!==void 0)switch(le.length){case 2:i.vertexAttrib2fv(re.location,le);break;case 3:i.vertexAttrib3fv(re.location,le);break;case 4:i.vertexAttrib4fv(re.location,le);break;default:i.vertexAttrib1fv(re.location,le)}}}}L()}function v(){A();for(const O in a){const k=a[O];for(const H in k){const q=k[H];for(const Z in q)g(q[Z].object),delete q[Z];delete k[H]}delete a[O]}}function b(O){if(a[O.id]===void 0)return;const k=a[O.id];for(const H in k){const q=k[H];for(const Z in q)g(q[Z].object),delete q[Z];delete k[H]}delete a[O.id]}function N(O){for(const k in a){const H=a[k];if(H[O.id]===void 0)continue;const q=H[O.id];for(const Z in q)g(q[Z].object),delete q[Z];delete H[O.id]}}function A(){I(),u=!0,c!==l&&(c=l,d(c.object))}function I(){l.geometry=null,l.program=null,l.wireframe=!1}return{setup:f,reset:A,resetDefaultState:I,dispose:v,releaseStatesOfGeometry:b,releaseStatesOfProgram:N,initAttributes:y,enableAttribute:S,disableUnusedAttributes:L}}function sM(i,e,t,n){const s=n.isWebGL2;let r;function o(u){r=u}function a(u,f){i.drawArrays(r,u,f),t.update(f,r,1)}function l(u,f,h){if(h===0)return;let d,g;if(s)d=i,g="drawArraysInstanced";else if(d=e.get("ANGLE_instanced_arrays"),g="drawArraysInstancedANGLE",d===null){console.error("THREE.WebGLBufferRenderer: using THREE.InstancedBufferGeometry but hardware does not support extension ANGLE_instanced_arrays.");return}d[g](r,u,f,h),t.update(f,r,h)}function c(u,f,h){if(h===0)return;const d=e.get("WEBGL_multi_draw");if(d===null)for(let g=0;g<h;g++)this.render(u[g],f[g]);else{d.multiDrawArraysWEBGL(r,u,0,f,0,h);let g=0;for(let _=0;_<h;_++)g+=f[_];t.update(g,r,1)}}this.setMode=o,this.render=a,this.renderInstances=l,this.renderMultiDraw=c}function rM(i,e,t){let n;function s(){if(n!==void 0)return n;if(e.has("EXT_texture_filter_anisotropic")===!0){const w=e.get("EXT_texture_filter_anisotropic");n=i.getParameter(w.MAX_TEXTURE_MAX_ANISOTROPY_EXT)}else n=0;return n}function r(w){if(w==="highp"){if(i.getShaderPrecisionFormat(i.VERTEX_SHADER,i.HIGH_FLOAT).precision>0&&i.getShaderPrecisionFormat(i.FRAGMENT_SHADER,i.HIGH_FLOAT).precision>0)return"highp";w="mediump"}return w==="mediump"&&i.getShaderPrecisionFormat(i.VERTEX_SHADER,i.MEDIUM_FLOAT).precision>0&&i.getShaderPrecisionFormat(i.FRAGMENT_SHADER,i.MEDIUM_FLOAT).precision>0?"mediump":"lowp"}const o=typeof WebGL2RenderingContext<"u"&&i.constructor.name==="WebGL2RenderingContext";let a=t.precision!==void 0?t.precision:"highp";const l=r(a);l!==a&&(console.warn("THREE.WebGLRenderer:",a,"not supported, using",l,"instead."),a=l);const c=o||e.has("WEBGL_draw_buffers"),u=t.logarithmicDepthBuffer===!0,f=i.getParameter(i.MAX_TEXTURE_IMAGE_UNITS),h=i.getParameter(i.MAX_VERTEX_TEXTURE_IMAGE_UNITS),d=i.getParameter(i.MAX_TEXTURE_SIZE),g=i.getParameter(i.MAX_CUBE_MAP_TEXTURE_SIZE),_=i.getParameter(i.MAX_VERTEX_ATTRIBS),m=i.getParameter(i.MAX_VERTEX_UNIFORM_VECTORS),p=i.getParameter(i.MAX_VARYING_VECTORS),x=i.getParameter(i.MAX_FRAGMENT_UNIFORM_VECTORS),y=h>0,S=o||e.has("OES_texture_float"),R=y&&S,L=o?i.getParameter(i.MAX_SAMPLES):0;return{isWebGL2:o,drawBuffers:c,getMaxAnisotropy:s,getMaxPrecision:r,precision:a,logarithmicDepthBuffer:u,maxTextures:f,maxVertexTextures:h,maxTextureSize:d,maxCubemapSize:g,maxAttributes:_,maxVertexUniforms:m,maxVaryings:p,maxFragmentUniforms:x,vertexTextures:y,floatFragmentTextures:S,floatVertexTextures:R,maxSamples:L}}function oM(i){const e=this;let t=null,n=0,s=!1,r=!1;const o=new Si,a=new je,l={value:null,needsUpdate:!1};this.uniform=l,this.numPlanes=0,this.numIntersection=0,this.init=function(f,h){const d=f.length!==0||h||n!==0||s;return s=h,n=f.length,d},this.beginShadows=function(){r=!0,u(null)},this.endShadows=function(){r=!1},this.setGlobalState=function(f,h){t=u(f,h,0)},this.setState=function(f,h,d){const g=f.clippingPlanes,_=f.clipIntersection,m=f.clipShadows,p=i.get(f);if(!s||g===null||g.length===0||r&&!m)r?u(null):c();else{const x=r?0:n,y=x*4;let S=p.clippingState||null;l.value=S,S=u(g,h,y,d);for(let R=0;R!==y;++R)S[R]=t[R];p.clippingState=S,this.numIntersection=_?this.numPlanes:0,this.numPlanes+=x}};function c(){l.value!==t&&(l.value=t,l.needsUpdate=n>0),e.numPlanes=n,e.numIntersection=0}function u(f,h,d,g){const _=f!==null?f.length:0;let m=null;if(_!==0){if(m=l.value,g!==!0||m===null){const p=d+_*4,x=h.matrixWorldInverse;a.getNormalMatrix(x),(m===null||m.length<p)&&(m=new Float32Array(p));for(let y=0,S=d;y!==_;++y,S+=4)o.copy(f[y]).applyMatrix4(x,a),o.normal.toArray(m,S),m[S+3]=o.constant}l.value=m,l.needsUpdate=!0}return e.numPlanes=_,e.numIntersection=0,m}}function aM(i){let e=new WeakMap;function t(o,a){return a===Fc?o.mapping=Rr:a===zc&&(o.mapping=Cr),o}function n(o){if(o&&o.isTexture){const a=o.mapping;if(a===Fc||a===zc)if(e.has(o)){const l=e.get(o).texture;return t(l,o.mapping)}else{const l=o.image;if(l&&l.height>0){const c=new xx(l.height/2);return c.fromEquirectangularTexture(i,o),e.set(o,c),o.addEventListener("dispose",s),t(c.texture,o.mapping)}else return null}}return o}function s(o){const a=o.target;a.removeEventListener("dispose",s);const l=e.get(a);l!==void 0&&(e.delete(a),l.dispose())}function r(){e=new WeakMap}return{get:n,dispose:r}}class cm extends om{constructor(e=-1,t=1,n=1,s=-1,r=.1,o=2e3){super(),this.isOrthographicCamera=!0,this.type="OrthographicCamera",this.zoom=1,this.view=null,this.left=e,this.right=t,this.top=n,this.bottom=s,this.near=r,this.far=o,this.updateProjectionMatrix()}copy(e,t){return super.copy(e,t),this.left=e.left,this.right=e.right,this.top=e.top,this.bottom=e.bottom,this.near=e.near,this.far=e.far,this.zoom=e.zoom,this.view=e.view===null?null:Object.assign({},e.view),this}setViewOffset(e,t,n,s,r,o){this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=e,this.view.fullHeight=t,this.view.offsetX=n,this.view.offsetY=s,this.view.width=r,this.view.height=o,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){const e=(this.right-this.left)/(2*this.zoom),t=(this.top-this.bottom)/(2*this.zoom),n=(this.right+this.left)/2,s=(this.top+this.bottom)/2;let r=n-e,o=n+e,a=s+t,l=s-t;if(this.view!==null&&this.view.enabled){const c=(this.right-this.left)/this.view.fullWidth/this.zoom,u=(this.top-this.bottom)/this.view.fullHeight/this.zoom;r+=c*this.view.offsetX,o=r+c*this.view.width,a-=u*this.view.offsetY,l=a-u*this.view.height}this.projectionMatrix.makeOrthographic(r,o,a,l,this.near,this.far,this.coordinateSystem),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(e){const t=super.toJSON(e);return t.object.zoom=this.zoom,t.object.left=this.left,t.object.right=this.right,t.object.top=this.top,t.object.bottom=this.bottom,t.object.near=this.near,t.object.far=this.far,this.view!==null&&(t.object.view=Object.assign({},this.view)),t}}const fr=4,Ih=[.125,.215,.35,.446,.526,.582],As=20,ac=new cm,Oh=new Qe;let lc=null,cc=0,uc=0;const Ms=(1+Math.sqrt(5))/2,lr=1/Ms,Nh=[new $(1,1,1),new $(-1,1,1),new $(1,1,-1),new $(-1,1,-1),new $(0,Ms,lr),new $(0,Ms,-lr),new $(lr,0,Ms),new $(-lr,0,Ms),new $(Ms,lr,0),new $(-Ms,lr,0)];class Fh{constructor(e){this._renderer=e,this._pingPongRenderTarget=null,this._lodMax=0,this._cubeSize=0,this._lodPlanes=[],this._sizeLods=[],this._sigmas=[],this._blurMaterial=null,this._cubemapMaterial=null,this._equirectMaterial=null,this._compileMaterial(this._blurMaterial)}fromScene(e,t=0,n=.1,s=100){lc=this._renderer.getRenderTarget(),cc=this._renderer.getActiveCubeFace(),uc=this._renderer.getActiveMipmapLevel(),this._setSize(256);const r=this._allocateTargets();return r.depthBuffer=!0,this._sceneToCubeUV(e,n,s,r),t>0&&this._blur(r,0,0,t),this._applyPMREM(r),this._cleanup(r),r}fromEquirectangular(e,t=null){return this._fromTexture(e,t)}fromCubemap(e,t=null){return this._fromTexture(e,t)}compileCubemapShader(){this._cubemapMaterial===null&&(this._cubemapMaterial=kh(),this._compileMaterial(this._cubemapMaterial))}compileEquirectangularShader(){this._equirectMaterial===null&&(this._equirectMaterial=Bh(),this._compileMaterial(this._equirectMaterial))}dispose(){this._dispose(),this._cubemapMaterial!==null&&this._cubemapMaterial.dispose(),this._equirectMaterial!==null&&this._equirectMaterial.dispose()}_setSize(e){this._lodMax=Math.floor(Math.log2(e)),this._cubeSize=Math.pow(2,this._lodMax)}_dispose(){this._blurMaterial!==null&&this._blurMaterial.dispose(),this._pingPongRenderTarget!==null&&this._pingPongRenderTarget.dispose();for(let e=0;e<this._lodPlanes.length;e++)this._lodPlanes[e].dispose()}_cleanup(e){this._renderer.setRenderTarget(lc,cc,uc),e.scissorTest=!1,da(e,0,0,e.width,e.height)}_fromTexture(e,t){e.mapping===Rr||e.mapping===Cr?this._setSize(e.image.length===0?16:e.image[0].width||e.image[0].image.width):this._setSize(e.image.width/4),lc=this._renderer.getRenderTarget(),cc=this._renderer.getActiveCubeFace(),uc=this._renderer.getActiveMipmapLevel();const n=t||this._allocateTargets();return this._textureToCubeUV(e,n),this._applyPMREM(n),this._cleanup(n),n}_allocateTargets(){const e=3*Math.max(this._cubeSize,112),t=4*this._cubeSize,n={magFilter:Dn,minFilter:Dn,generateMipmaps:!1,type:So,format:Xn,colorSpace:Di,depthBuffer:!1},s=zh(e,t,n);if(this._pingPongRenderTarget===null||this._pingPongRenderTarget.width!==e||this._pingPongRenderTarget.height!==t){this._pingPongRenderTarget!==null&&this._dispose(),this._pingPongRenderTarget=zh(e,t,n);const{_lodMax:r}=this;({sizeLods:this._sizeLods,lodPlanes:this._lodPlanes,sigmas:this._sigmas}=lM(r)),this._blurMaterial=cM(r,e,t)}return s}_compileMaterial(e){const t=new Yi(this._lodPlanes[0],e);this._renderer.compile(t,ac)}_sceneToCubeUV(e,t,n,s){const a=new Un(90,1,t,n),l=[1,-1,1,1,1,1],c=[1,1,1,-1,-1,-1],u=this._renderer,f=u.autoClear,h=u.toneMapping;u.getClearColor(Oh),u.toneMapping=Qi,u.autoClear=!1;const d=new nm({name:"PMREM.Background",side:un,depthWrite:!1,depthTest:!1}),g=new Yi(new Fo,d);let _=!1;const m=e.background;m?m.isColor&&(d.color.copy(m),e.background=null,_=!0):(d.color.copy(Oh),_=!0);for(let p=0;p<6;p++){const x=p%3;x===0?(a.up.set(0,l[p],0),a.lookAt(c[p],0,0)):x===1?(a.up.set(0,0,l[p]),a.lookAt(0,c[p],0)):(a.up.set(0,l[p],0),a.lookAt(0,0,c[p]));const y=this._cubeSize;da(s,x*y,p>2?y:0,y,y),u.setRenderTarget(s),_&&u.render(g,a),u.render(e,a)}g.geometry.dispose(),g.material.dispose(),u.toneMapping=h,u.autoClear=f,e.background=m}_textureToCubeUV(e,t){const n=this._renderer,s=e.mapping===Rr||e.mapping===Cr;s?(this._cubemapMaterial===null&&(this._cubemapMaterial=kh()),this._cubemapMaterial.uniforms.flipEnvMap.value=e.isRenderTargetTexture===!1?-1:1):this._equirectMaterial===null&&(this._equirectMaterial=Bh());const r=s?this._cubemapMaterial:this._equirectMaterial,o=new Yi(this._lodPlanes[0],r),a=r.uniforms;a.envMap.value=e;const l=this._cubeSize;da(t,0,0,3*l,2*l),n.setRenderTarget(t),n.render(o,ac)}_applyPMREM(e){const t=this._renderer,n=t.autoClear;t.autoClear=!1;for(let s=1;s<this._lodPlanes.length;s++){const r=Math.sqrt(this._sigmas[s]*this._sigmas[s]-this._sigmas[s-1]*this._sigmas[s-1]),o=Nh[(s-1)%Nh.length];this._blur(e,s-1,s,r,o)}t.autoClear=n}_blur(e,t,n,s,r){const o=this._pingPongRenderTarget;this._halfBlur(e,o,t,n,s,"latitudinal",r),this._halfBlur(o,e,n,n,s,"longitudinal",r)}_halfBlur(e,t,n,s,r,o,a){const l=this._renderer,c=this._blurMaterial;o!=="latitudinal"&&o!=="longitudinal"&&console.error("blur direction must be either latitudinal or longitudinal!");const u=3,f=new Yi(this._lodPlanes[s],c),h=c.uniforms,d=this._sizeLods[n]-1,g=isFinite(r)?Math.PI/(2*d):2*Math.PI/(2*As-1),_=r/g,m=isFinite(r)?1+Math.floor(u*_):As;m>As&&console.warn(`sigmaRadians, ${r}, is too large and will clip, as it requested ${m} samples when the maximum is set to ${As}`);const p=[];let x=0;for(let w=0;w<As;++w){const B=w/_,v=Math.exp(-B*B/2);p.push(v),w===0?x+=v:w<m&&(x+=2*v)}for(let w=0;w<p.length;w++)p[w]=p[w]/x;h.envMap.value=e.texture,h.samples.value=m,h.weights.value=p,h.latitudinal.value=o==="latitudinal",a&&(h.poleAxis.value=a);const{_lodMax:y}=this;h.dTheta.value=g,h.mipInt.value=y-n;const S=this._sizeLods[s],R=3*S*(s>y-fr?s-y+fr:0),L=4*(this._cubeSize-S);da(t,R,L,3*S,2*S),l.setRenderTarget(t),l.render(f,ac)}}function lM(i){const e=[],t=[],n=[];let s=i;const r=i-fr+1+Ih.length;for(let o=0;o<r;o++){const a=Math.pow(2,s);t.push(a);let l=1/a;o>i-fr?l=Ih[o-i+fr-1]:o===0&&(l=0),n.push(l);const c=1/(a-2),u=-c,f=1+c,h=[u,u,f,u,f,f,u,u,f,f,u,f],d=6,g=6,_=3,m=2,p=1,x=new Float32Array(_*g*d),y=new Float32Array(m*g*d),S=new Float32Array(p*g*d);for(let L=0;L<d;L++){const w=L%3*2/3-1,B=L>2?0:-1,v=[w,B,0,w+2/3,B,0,w+2/3,B+1,0,w,B,0,w+2/3,B+1,0,w,B+1,0];x.set(v,_*g*L),y.set(h,m*g*L);const b=[L,L,L,L,L,L];S.set(b,p*g*L)}const R=new Ni;R.setAttribute("position",new Bn(x,_)),R.setAttribute("uv",new Bn(y,m)),R.setAttribute("faceIndex",new Bn(S,p)),e.push(R),s>fr&&s--}return{lodPlanes:e,sizeLods:t,sigmas:n}}function zh(i,e,t){const n=new Bs(i,e,t);return n.texture.mapping=pl,n.texture.name="PMREM.cubeUv",n.scissorTest=!0,n}function da(i,e,t,n,s){i.viewport.set(e,t,n,s),i.scissor.set(e,t,n,s)}function cM(i,e,t){const n=new Float32Array(As),s=new $(0,1,0);return new rs({name:"SphericalGaussianBlur",defines:{n:As,CUBEUV_TEXEL_WIDTH:1/e,CUBEUV_TEXEL_HEIGHT:1/t,CUBEUV_MAX_MIP:`${i}.0`},uniforms:{envMap:{value:null},samples:{value:1},weights:{value:n},latitudinal:{value:!1},dTheta:{value:0},mipInt:{value:0},poleAxis:{value:s}},vertexShader:Pu(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;
			uniform int samples;
			uniform float weights[ n ];
			uniform bool latitudinal;
			uniform float dTheta;
			uniform float mipInt;
			uniform vec3 poleAxis;

			#define ENVMAP_TYPE_CUBE_UV
			#include <cube_uv_reflection_fragment>

			vec3 getSample( float theta, vec3 axis ) {

				float cosTheta = cos( theta );
				// Rodrigues' axis-angle rotation
				vec3 sampleDirection = vOutputDirection * cosTheta
					+ cross( axis, vOutputDirection ) * sin( theta )
					+ axis * dot( axis, vOutputDirection ) * ( 1.0 - cosTheta );

				return bilinearCubeUV( envMap, sampleDirection, mipInt );

			}

			void main() {

				vec3 axis = latitudinal ? poleAxis : cross( poleAxis, vOutputDirection );

				if ( all( equal( axis, vec3( 0.0 ) ) ) ) {

					axis = vec3( vOutputDirection.z, 0.0, - vOutputDirection.x );

				}

				axis = normalize( axis );

				gl_FragColor = vec4( 0.0, 0.0, 0.0, 1.0 );
				gl_FragColor.rgb += weights[ 0 ] * getSample( 0.0, axis );

				for ( int i = 1; i < n; i++ ) {

					if ( i >= samples ) {

						break;

					}

					float theta = dTheta * float( i );
					gl_FragColor.rgb += weights[ i ] * getSample( -1.0 * theta, axis );
					gl_FragColor.rgb += weights[ i ] * getSample( theta, axis );

				}

			}
		`,blending:Zi,depthTest:!1,depthWrite:!1})}function Bh(){return new rs({name:"EquirectangularToCubeUV",uniforms:{envMap:{value:null}},vertexShader:Pu(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;

			#include <common>

			void main() {

				vec3 outputDirection = normalize( vOutputDirection );
				vec2 uv = equirectUv( outputDirection );

				gl_FragColor = vec4( texture2D ( envMap, uv ).rgb, 1.0 );

			}
		`,blending:Zi,depthTest:!1,depthWrite:!1})}function kh(){return new rs({name:"CubemapToCubeUV",uniforms:{envMap:{value:null},flipEnvMap:{value:-1}},vertexShader:Pu(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			uniform float flipEnvMap;

			varying vec3 vOutputDirection;

			uniform samplerCube envMap;

			void main() {

				gl_FragColor = textureCube( envMap, vec3( flipEnvMap * vOutputDirection.x, vOutputDirection.yz ) );

			}
		`,blending:Zi,depthTest:!1,depthWrite:!1})}function Pu(){return`

		precision mediump float;
		precision mediump int;

		attribute float faceIndex;

		varying vec3 vOutputDirection;

		// RH coordinate system; PMREM face-indexing convention
		vec3 getDirection( vec2 uv, float face ) {

			uv = 2.0 * uv - 1.0;

			vec3 direction = vec3( uv, 1.0 );

			if ( face == 0.0 ) {

				direction = direction.zyx; // ( 1, v, u ) pos x

			} else if ( face == 1.0 ) {

				direction = direction.xzy;
				direction.xz *= -1.0; // ( -u, 1, -v ) pos y

			} else if ( face == 2.0 ) {

				direction.x *= -1.0; // ( -u, v, 1 ) pos z

			} else if ( face == 3.0 ) {

				direction = direction.zyx;
				direction.xz *= -1.0; // ( -1, v, -u ) neg x

			} else if ( face == 4.0 ) {

				direction = direction.xzy;
				direction.xy *= -1.0; // ( -u, -1, v ) neg y

			} else if ( face == 5.0 ) {

				direction.z *= -1.0; // ( u, v, -1 ) neg z

			}

			return direction;

		}

		void main() {

			vOutputDirection = getDirection( uv, faceIndex );
			gl_Position = vec4( position, 1.0 );

		}
	`}function uM(i){let e=new WeakMap,t=null;function n(a){if(a&&a.isTexture){const l=a.mapping,c=l===Fc||l===zc,u=l===Rr||l===Cr;if(c||u)if(a.isRenderTargetTexture&&a.needsPMREMUpdate===!0){a.needsPMREMUpdate=!1;let f=e.get(a);return t===null&&(t=new Fh(i)),f=c?t.fromEquirectangular(a,f):t.fromCubemap(a,f),e.set(a,f),f.texture}else{if(e.has(a))return e.get(a).texture;{const f=a.image;if(c&&f&&f.height>0||u&&f&&s(f)){t===null&&(t=new Fh(i));const h=c?t.fromEquirectangular(a):t.fromCubemap(a);return e.set(a,h),a.addEventListener("dispose",r),h.texture}else return null}}}return a}function s(a){let l=0;const c=6;for(let u=0;u<c;u++)a[u]!==void 0&&l++;return l===c}function r(a){const l=a.target;l.removeEventListener("dispose",r);const c=e.get(l);c!==void 0&&(e.delete(l),c.dispose())}function o(){e=new WeakMap,t!==null&&(t.dispose(),t=null)}return{get:n,dispose:o}}function fM(i){const e={};function t(n){if(e[n]!==void 0)return e[n];let s;switch(n){case"WEBGL_depth_texture":s=i.getExtension("WEBGL_depth_texture")||i.getExtension("MOZ_WEBGL_depth_texture")||i.getExtension("WEBKIT_WEBGL_depth_texture");break;case"EXT_texture_filter_anisotropic":s=i.getExtension("EXT_texture_filter_anisotropic")||i.getExtension("MOZ_EXT_texture_filter_anisotropic")||i.getExtension("WEBKIT_EXT_texture_filter_anisotropic");break;case"WEBGL_compressed_texture_s3tc":s=i.getExtension("WEBGL_compressed_texture_s3tc")||i.getExtension("MOZ_WEBGL_compressed_texture_s3tc")||i.getExtension("WEBKIT_WEBGL_compressed_texture_s3tc");break;case"WEBGL_compressed_texture_pvrtc":s=i.getExtension("WEBGL_compressed_texture_pvrtc")||i.getExtension("WEBKIT_WEBGL_compressed_texture_pvrtc");break;default:s=i.getExtension(n)}return e[n]=s,s}return{has:function(n){return t(n)!==null},init:function(n){n.isWebGL2?(t("EXT_color_buffer_float"),t("WEBGL_clip_cull_distance")):(t("WEBGL_depth_texture"),t("OES_texture_float"),t("OES_texture_half_float"),t("OES_texture_half_float_linear"),t("OES_standard_derivatives"),t("OES_element_index_uint"),t("OES_vertex_array_object"),t("ANGLE_instanced_arrays")),t("OES_texture_float_linear"),t("EXT_color_buffer_half_float"),t("WEBGL_multisampled_render_to_texture")},get:function(n){const s=t(n);return s===null&&console.warn("THREE.WebGLRenderer: "+n+" extension not supported."),s}}}function hM(i,e,t,n){const s={},r=new WeakMap;function o(f){const h=f.target;h.index!==null&&e.remove(h.index);for(const g in h.attributes)e.remove(h.attributes[g]);for(const g in h.morphAttributes){const _=h.morphAttributes[g];for(let m=0,p=_.length;m<p;m++)e.remove(_[m])}h.removeEventListener("dispose",o),delete s[h.id];const d=r.get(h);d&&(e.remove(d),r.delete(h)),n.releaseStatesOfGeometry(h),h.isInstancedBufferGeometry===!0&&delete h._maxInstanceCount,t.memory.geometries--}function a(f,h){return s[h.id]===!0||(h.addEventListener("dispose",o),s[h.id]=!0,t.memory.geometries++),h}function l(f){const h=f.attributes;for(const g in h)e.update(h[g],i.ARRAY_BUFFER);const d=f.morphAttributes;for(const g in d){const _=d[g];for(let m=0,p=_.length;m<p;m++)e.update(_[m],i.ARRAY_BUFFER)}}function c(f){const h=[],d=f.index,g=f.attributes.position;let _=0;if(d!==null){const x=d.array;_=d.version;for(let y=0,S=x.length;y<S;y+=3){const R=x[y+0],L=x[y+1],w=x[y+2];h.push(R,L,L,w,w,R)}}else if(g!==void 0){const x=g.array;_=g.version;for(let y=0,S=x.length/3-1;y<S;y+=3){const R=y+0,L=y+1,w=y+2;h.push(R,L,L,w,w,R)}}else return;const m=new(Zp(h)?sm:im)(h,1);m.version=_;const p=r.get(f);p&&e.remove(p),r.set(f,m)}function u(f){const h=r.get(f);if(h){const d=f.index;d!==null&&h.version<d.version&&c(f)}else c(f);return r.get(f)}return{get:a,update:l,getWireframeAttribute:u}}function dM(i,e,t,n){const s=n.isWebGL2;let r;function o(d){r=d}let a,l;function c(d){a=d.type,l=d.bytesPerElement}function u(d,g){i.drawElements(r,g,a,d*l),t.update(g,r,1)}function f(d,g,_){if(_===0)return;let m,p;if(s)m=i,p="drawElementsInstanced";else if(m=e.get("ANGLE_instanced_arrays"),p="drawElementsInstancedANGLE",m===null){console.error("THREE.WebGLIndexedBufferRenderer: using THREE.InstancedBufferGeometry but hardware does not support extension ANGLE_instanced_arrays.");return}m[p](r,g,a,d*l,_),t.update(g,r,_)}function h(d,g,_){if(_===0)return;const m=e.get("WEBGL_multi_draw");if(m===null)for(let p=0;p<_;p++)this.render(d[p]/l,g[p]);else{m.multiDrawElementsWEBGL(r,g,0,a,d,0,_);let p=0;for(let x=0;x<_;x++)p+=g[x];t.update(p,r,1)}}this.setMode=o,this.setIndex=c,this.render=u,this.renderInstances=f,this.renderMultiDraw=h}function pM(i){const e={geometries:0,textures:0},t={frame:0,calls:0,triangles:0,points:0,lines:0};function n(r,o,a){switch(t.calls++,o){case i.TRIANGLES:t.triangles+=a*(r/3);break;case i.LINES:t.lines+=a*(r/2);break;case i.LINE_STRIP:t.lines+=a*(r-1);break;case i.LINE_LOOP:t.lines+=a*r;break;case i.POINTS:t.points+=a*r;break;default:console.error("THREE.WebGLInfo: Unknown draw mode:",o);break}}function s(){t.calls=0,t.triangles=0,t.points=0,t.lines=0}return{memory:e,render:t,programs:null,autoReset:!0,reset:s,update:n}}function mM(i,e){return i[0]-e[0]}function _M(i,e){return Math.abs(e[1])-Math.abs(i[1])}function gM(i,e,t){const n={},s=new Float32Array(8),r=new WeakMap,o=new Ft,a=[];for(let c=0;c<8;c++)a[c]=[c,0];function l(c,u,f){const h=c.morphTargetInfluences;if(e.isWebGL2===!0){const g=u.morphAttributes.position||u.morphAttributes.normal||u.morphAttributes.color,_=g!==void 0?g.length:0;let m=r.get(u);if(m===void 0||m.count!==_){let k=function(){I.dispose(),r.delete(u),u.removeEventListener("dispose",k)};var d=k;m!==void 0&&m.texture.dispose();const y=u.morphAttributes.position!==void 0,S=u.morphAttributes.normal!==void 0,R=u.morphAttributes.color!==void 0,L=u.morphAttributes.position||[],w=u.morphAttributes.normal||[],B=u.morphAttributes.color||[];let v=0;y===!0&&(v=1),S===!0&&(v=2),R===!0&&(v=3);let b=u.attributes.position.count*v,N=1;b>e.maxTextureSize&&(N=Math.ceil(b/e.maxTextureSize),b=e.maxTextureSize);const A=new Float32Array(b*N*4*_),I=new em(A,b,N,_);I.type=qi,I.needsUpdate=!0;const O=v*4;for(let H=0;H<_;H++){const q=L[H],Z=w[H],W=B[H],j=b*N*4*H;for(let G=0;G<q.count;G++){const re=G*O;y===!0&&(o.fromBufferAttribute(q,G),A[j+re+0]=o.x,A[j+re+1]=o.y,A[j+re+2]=o.z,A[j+re+3]=0),S===!0&&(o.fromBufferAttribute(Z,G),A[j+re+4]=o.x,A[j+re+5]=o.y,A[j+re+6]=o.z,A[j+re+7]=0),R===!0&&(o.fromBufferAttribute(W,G),A[j+re+8]=o.x,A[j+re+9]=o.y,A[j+re+10]=o.z,A[j+re+11]=W.itemSize===4?o.w:1)}}m={count:_,texture:I,size:new He(b,N)},r.set(u,m),u.addEventListener("dispose",k)}let p=0;for(let y=0;y<h.length;y++)p+=h[y];const x=u.morphTargetsRelative?1:1-p;f.getUniforms().setValue(i,"morphTargetBaseInfluence",x),f.getUniforms().setValue(i,"morphTargetInfluences",h),f.getUniforms().setValue(i,"morphTargetsTexture",m.texture,t),f.getUniforms().setValue(i,"morphTargetsTextureSize",m.size)}else{const g=h===void 0?0:h.length;let _=n[u.id];if(_===void 0||_.length!==g){_=[];for(let S=0;S<g;S++)_[S]=[S,0];n[u.id]=_}for(let S=0;S<g;S++){const R=_[S];R[0]=S,R[1]=h[S]}_.sort(_M);for(let S=0;S<8;S++)S<g&&_[S][1]?(a[S][0]=_[S][0],a[S][1]=_[S][1]):(a[S][0]=Number.MAX_SAFE_INTEGER,a[S][1]=0);a.sort(mM);const m=u.morphAttributes.position,p=u.morphAttributes.normal;let x=0;for(let S=0;S<8;S++){const R=a[S],L=R[0],w=R[1];L!==Number.MAX_SAFE_INTEGER&&w?(m&&u.getAttribute("morphTarget"+S)!==m[L]&&u.setAttribute("morphTarget"+S,m[L]),p&&u.getAttribute("morphNormal"+S)!==p[L]&&u.setAttribute("morphNormal"+S,p[L]),s[S]=w,x+=w):(m&&u.hasAttribute("morphTarget"+S)===!0&&u.deleteAttribute("morphTarget"+S),p&&u.hasAttribute("morphNormal"+S)===!0&&u.deleteAttribute("morphNormal"+S),s[S]=0)}const y=u.morphTargetsRelative?1:1-x;f.getUniforms().setValue(i,"morphTargetBaseInfluence",y),f.getUniforms().setValue(i,"morphTargetInfluences",s)}}return{update:l}}function vM(i,e,t,n){let s=new WeakMap;function r(l){const c=n.render.frame,u=l.geometry,f=e.get(l,u);if(s.get(f)!==c&&(e.update(f),s.set(f,c)),l.isInstancedMesh&&(l.hasEventListener("dispose",a)===!1&&l.addEventListener("dispose",a),s.get(l)!==c&&(t.update(l.instanceMatrix,i.ARRAY_BUFFER),l.instanceColor!==null&&t.update(l.instanceColor,i.ARRAY_BUFFER),s.set(l,c))),l.isSkinnedMesh){const h=l.skeleton;s.get(h)!==c&&(h.update(),s.set(h,c))}return f}function o(){s=new WeakMap}function a(l){const c=l.target;c.removeEventListener("dispose",a),t.remove(c.instanceMatrix),c.instanceColor!==null&&t.remove(c.instanceColor)}return{update:r,dispose:o}}class um extends Tn{constructor(e,t,n,s,r,o,a,l,c,u){if(u=u!==void 0?u:Ds,u!==Ds&&u!==Pr)throw new Error("DepthTexture format must be either THREE.DepthFormat or THREE.DepthStencilFormat");n===void 0&&u===Ds&&(n=Xi),n===void 0&&u===Pr&&(n=Ls),super(null,s,r,o,a,l,u,n,c),this.isDepthTexture=!0,this.image={width:e,height:t},this.magFilter=a!==void 0?a:tn,this.minFilter=l!==void 0?l:tn,this.flipY=!1,this.generateMipmaps=!1,this.compareFunction=null}copy(e){return super.copy(e),this.compareFunction=e.compareFunction,this}toJSON(e){const t=super.toJSON(e);return this.compareFunction!==null&&(t.compareFunction=this.compareFunction),t}}const fm=new Tn,hm=new um(1,1);hm.compareFunction=Kp;const dm=new em,pm=new nx,mm=new am,Vh=[],Hh=[],Gh=new Float32Array(16),Wh=new Float32Array(9),Xh=new Float32Array(4);function zr(i,e,t){const n=i[0];if(n<=0||n>0)return i;const s=e*t;let r=Vh[s];if(r===void 0&&(r=new Float32Array(s),Vh[s]=r),e!==0){n.toArray(r,0);for(let o=1,a=0;o!==e;++o)a+=t,i[o].toArray(r,a)}return r}function Dt(i,e){if(i.length!==e.length)return!1;for(let t=0,n=i.length;t<n;t++)if(i[t]!==e[t])return!1;return!0}function Ut(i,e){for(let t=0,n=e.length;t<n;t++)i[t]=e[t]}function xl(i,e){let t=Hh[e];t===void 0&&(t=new Int32Array(e),Hh[e]=t);for(let n=0;n!==e;++n)t[n]=i.allocateTextureUnit();return t}function xM(i,e){const t=this.cache;t[0]!==e&&(i.uniform1f(this.addr,e),t[0]=e)}function yM(i,e){const t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y)&&(i.uniform2f(this.addr,e.x,e.y),t[0]=e.x,t[1]=e.y);else{if(Dt(t,e))return;i.uniform2fv(this.addr,e),Ut(t,e)}}function SM(i,e){const t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z)&&(i.uniform3f(this.addr,e.x,e.y,e.z),t[0]=e.x,t[1]=e.y,t[2]=e.z);else if(e.r!==void 0)(t[0]!==e.r||t[1]!==e.g||t[2]!==e.b)&&(i.uniform3f(this.addr,e.r,e.g,e.b),t[0]=e.r,t[1]=e.g,t[2]=e.b);else{if(Dt(t,e))return;i.uniform3fv(this.addr,e),Ut(t,e)}}function MM(i,e){const t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z||t[3]!==e.w)&&(i.uniform4f(this.addr,e.x,e.y,e.z,e.w),t[0]=e.x,t[1]=e.y,t[2]=e.z,t[3]=e.w);else{if(Dt(t,e))return;i.uniform4fv(this.addr,e),Ut(t,e)}}function EM(i,e){const t=this.cache,n=e.elements;if(n===void 0){if(Dt(t,e))return;i.uniformMatrix2fv(this.addr,!1,e),Ut(t,e)}else{if(Dt(t,n))return;Xh.set(n),i.uniformMatrix2fv(this.addr,!1,Xh),Ut(t,n)}}function bM(i,e){const t=this.cache,n=e.elements;if(n===void 0){if(Dt(t,e))return;i.uniformMatrix3fv(this.addr,!1,e),Ut(t,e)}else{if(Dt(t,n))return;Wh.set(n),i.uniformMatrix3fv(this.addr,!1,Wh),Ut(t,n)}}function TM(i,e){const t=this.cache,n=e.elements;if(n===void 0){if(Dt(t,e))return;i.uniformMatrix4fv(this.addr,!1,e),Ut(t,e)}else{if(Dt(t,n))return;Gh.set(n),i.uniformMatrix4fv(this.addr,!1,Gh),Ut(t,n)}}function AM(i,e){const t=this.cache;t[0]!==e&&(i.uniform1i(this.addr,e),t[0]=e)}function wM(i,e){const t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y)&&(i.uniform2i(this.addr,e.x,e.y),t[0]=e.x,t[1]=e.y);else{if(Dt(t,e))return;i.uniform2iv(this.addr,e),Ut(t,e)}}function RM(i,e){const t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z)&&(i.uniform3i(this.addr,e.x,e.y,e.z),t[0]=e.x,t[1]=e.y,t[2]=e.z);else{if(Dt(t,e))return;i.uniform3iv(this.addr,e),Ut(t,e)}}function CM(i,e){const t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z||t[3]!==e.w)&&(i.uniform4i(this.addr,e.x,e.y,e.z,e.w),t[0]=e.x,t[1]=e.y,t[2]=e.z,t[3]=e.w);else{if(Dt(t,e))return;i.uniform4iv(this.addr,e),Ut(t,e)}}function PM(i,e){const t=this.cache;t[0]!==e&&(i.uniform1ui(this.addr,e),t[0]=e)}function LM(i,e){const t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y)&&(i.uniform2ui(this.addr,e.x,e.y),t[0]=e.x,t[1]=e.y);else{if(Dt(t,e))return;i.uniform2uiv(this.addr,e),Ut(t,e)}}function DM(i,e){const t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z)&&(i.uniform3ui(this.addr,e.x,e.y,e.z),t[0]=e.x,t[1]=e.y,t[2]=e.z);else{if(Dt(t,e))return;i.uniform3uiv(this.addr,e),Ut(t,e)}}function UM(i,e){const t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z||t[3]!==e.w)&&(i.uniform4ui(this.addr,e.x,e.y,e.z,e.w),t[0]=e.x,t[1]=e.y,t[2]=e.z,t[3]=e.w);else{if(Dt(t,e))return;i.uniform4uiv(this.addr,e),Ut(t,e)}}function IM(i,e,t){const n=this.cache,s=t.allocateTextureUnit();n[0]!==s&&(i.uniform1i(this.addr,s),n[0]=s);const r=this.type===i.SAMPLER_2D_SHADOW?hm:fm;t.setTexture2D(e||r,s)}function OM(i,e,t){const n=this.cache,s=t.allocateTextureUnit();n[0]!==s&&(i.uniform1i(this.addr,s),n[0]=s),t.setTexture3D(e||pm,s)}function NM(i,e,t){const n=this.cache,s=t.allocateTextureUnit();n[0]!==s&&(i.uniform1i(this.addr,s),n[0]=s),t.setTextureCube(e||mm,s)}function FM(i,e,t){const n=this.cache,s=t.allocateTextureUnit();n[0]!==s&&(i.uniform1i(this.addr,s),n[0]=s),t.setTexture2DArray(e||dm,s)}function zM(i){switch(i){case 5126:return xM;case 35664:return yM;case 35665:return SM;case 35666:return MM;case 35674:return EM;case 35675:return bM;case 35676:return TM;case 5124:case 35670:return AM;case 35667:case 35671:return wM;case 35668:case 35672:return RM;case 35669:case 35673:return CM;case 5125:return PM;case 36294:return LM;case 36295:return DM;case 36296:return UM;case 35678:case 36198:case 36298:case 36306:case 35682:return IM;case 35679:case 36299:case 36307:return OM;case 35680:case 36300:case 36308:case 36293:return NM;case 36289:case 36303:case 36311:case 36292:return FM}}function BM(i,e){i.uniform1fv(this.addr,e)}function kM(i,e){const t=zr(e,this.size,2);i.uniform2fv(this.addr,t)}function VM(i,e){const t=zr(e,this.size,3);i.uniform3fv(this.addr,t)}function HM(i,e){const t=zr(e,this.size,4);i.uniform4fv(this.addr,t)}function GM(i,e){const t=zr(e,this.size,4);i.uniformMatrix2fv(this.addr,!1,t)}function WM(i,e){const t=zr(e,this.size,9);i.uniformMatrix3fv(this.addr,!1,t)}function XM(i,e){const t=zr(e,this.size,16);i.uniformMatrix4fv(this.addr,!1,t)}function qM(i,e){i.uniform1iv(this.addr,e)}function YM(i,e){i.uniform2iv(this.addr,e)}function $M(i,e){i.uniform3iv(this.addr,e)}function jM(i,e){i.uniform4iv(this.addr,e)}function KM(i,e){i.uniform1uiv(this.addr,e)}function ZM(i,e){i.uniform2uiv(this.addr,e)}function JM(i,e){i.uniform3uiv(this.addr,e)}function QM(i,e){i.uniform4uiv(this.addr,e)}function eE(i,e,t){const n=this.cache,s=e.length,r=xl(t,s);Dt(n,r)||(i.uniform1iv(this.addr,r),Ut(n,r));for(let o=0;o!==s;++o)t.setTexture2D(e[o]||fm,r[o])}function tE(i,e,t){const n=this.cache,s=e.length,r=xl(t,s);Dt(n,r)||(i.uniform1iv(this.addr,r),Ut(n,r));for(let o=0;o!==s;++o)t.setTexture3D(e[o]||pm,r[o])}function nE(i,e,t){const n=this.cache,s=e.length,r=xl(t,s);Dt(n,r)||(i.uniform1iv(this.addr,r),Ut(n,r));for(let o=0;o!==s;++o)t.setTextureCube(e[o]||mm,r[o])}function iE(i,e,t){const n=this.cache,s=e.length,r=xl(t,s);Dt(n,r)||(i.uniform1iv(this.addr,r),Ut(n,r));for(let o=0;o!==s;++o)t.setTexture2DArray(e[o]||dm,r[o])}function sE(i){switch(i){case 5126:return BM;case 35664:return kM;case 35665:return VM;case 35666:return HM;case 35674:return GM;case 35675:return WM;case 35676:return XM;case 5124:case 35670:return qM;case 35667:case 35671:return YM;case 35668:case 35672:return $M;case 35669:case 35673:return jM;case 5125:return KM;case 36294:return ZM;case 36295:return JM;case 36296:return QM;case 35678:case 36198:case 36298:case 36306:case 35682:return eE;case 35679:case 36299:case 36307:return tE;case 35680:case 36300:case 36308:case 36293:return nE;case 36289:case 36303:case 36311:case 36292:return iE}}class rE{constructor(e,t,n){this.id=e,this.addr=n,this.cache=[],this.type=t.type,this.setValue=zM(t.type)}}class oE{constructor(e,t,n){this.id=e,this.addr=n,this.cache=[],this.type=t.type,this.size=t.size,this.setValue=sE(t.type)}}class aE{constructor(e){this.id=e,this.seq=[],this.map={}}setValue(e,t,n){const s=this.seq;for(let r=0,o=s.length;r!==o;++r){const a=s[r];a.setValue(e,t[a.id],n)}}}const fc=/(\w+)(\])?(\[|\.)?/g;function qh(i,e){i.seq.push(e),i.map[e.id]=e}function lE(i,e,t){const n=i.name,s=n.length;for(fc.lastIndex=0;;){const r=fc.exec(n),o=fc.lastIndex;let a=r[1];const l=r[2]==="]",c=r[3];if(l&&(a=a|0),c===void 0||c==="["&&o+2===s){qh(t,c===void 0?new rE(a,i,e):new oE(a,i,e));break}else{let f=t.map[a];f===void 0&&(f=new aE(a),qh(t,f)),t=f}}}class wa{constructor(e,t){this.seq=[],this.map={};const n=e.getProgramParameter(t,e.ACTIVE_UNIFORMS);for(let s=0;s<n;++s){const r=e.getActiveUniform(t,s),o=e.getUniformLocation(t,r.name);lE(r,o,this)}}setValue(e,t,n,s){const r=this.map[t];r!==void 0&&r.setValue(e,n,s)}setOptional(e,t,n){const s=t[n];s!==void 0&&this.setValue(e,n,s)}static upload(e,t,n,s){for(let r=0,o=t.length;r!==o;++r){const a=t[r],l=n[a.id];l.needsUpdate!==!1&&a.setValue(e,l.value,s)}}static seqWithValue(e,t){const n=[];for(let s=0,r=e.length;s!==r;++s){const o=e[s];o.id in t&&n.push(o)}return n}}function Yh(i,e,t){const n=i.createShader(e);return i.shaderSource(n,t),i.compileShader(n),n}const cE=37297;let uE=0;function fE(i,e){const t=i.split(`
`),n=[],s=Math.max(e-6,0),r=Math.min(e+6,t.length);for(let o=s;o<r;o++){const a=o+1;n.push(`${a===e?">":" "} ${a}: ${t[o]}`)}return n.join(`
`)}function hE(i){const e=at.getPrimaries(at.workingColorSpace),t=at.getPrimaries(i);let n;switch(e===t?n="":e===Wa&&t===Ga?n="LinearDisplayP3ToLinearSRGB":e===Ga&&t===Wa&&(n="LinearSRGBToLinearDisplayP3"),i){case Di:case ml:return[n,"LinearTransferOETF"];case kt:case Au:return[n,"sRGBTransferOETF"];default:return console.warn("THREE.WebGLProgram: Unsupported color space:",i),[n,"LinearTransferOETF"]}}function $h(i,e,t){const n=i.getShaderParameter(e,i.COMPILE_STATUS),s=i.getShaderInfoLog(e).trim();if(n&&s==="")return"";const r=/ERROR: 0:(\d+)/.exec(s);if(r){const o=parseInt(r[1]);return t.toUpperCase()+`

`+s+`

`+fE(i.getShaderSource(e),o)}else return s}function dE(i,e){const t=hE(e);return`vec4 ${i}( vec4 value ) { return ${t[0]}( ${t[1]}( value ) ); }`}function pE(i,e){let t;switch(e){case Ev:t="Linear";break;case bv:t="Reinhard";break;case Tv:t="OptimizedCineon";break;case Av:t="ACESFilmic";break;case Rv:t="AgX";break;case wv:t="Custom";break;default:console.warn("THREE.WebGLProgram: Unsupported toneMapping:",e),t="Linear"}return"vec3 "+i+"( vec3 color ) { return "+t+"ToneMapping( color ); }"}function mE(i){return[i.extensionDerivatives||i.envMapCubeUVHeight||i.bumpMap||i.normalMapTangentSpace||i.clearcoatNormalMap||i.flatShading||i.shaderID==="physical"?"#extension GL_OES_standard_derivatives : enable":"",(i.extensionFragDepth||i.logarithmicDepthBuffer)&&i.rendererExtensionFragDepth?"#extension GL_EXT_frag_depth : enable":"",i.extensionDrawBuffers&&i.rendererExtensionDrawBuffers?"#extension GL_EXT_draw_buffers : require":"",(i.extensionShaderTextureLOD||i.envMap||i.transmission)&&i.rendererExtensionShaderTextureLod?"#extension GL_EXT_shader_texture_lod : enable":""].filter(hr).join(`
`)}function _E(i){return[i.extensionClipCullDistance?"#extension GL_ANGLE_clip_cull_distance : require":""].filter(hr).join(`
`)}function gE(i){const e=[];for(const t in i){const n=i[t];n!==!1&&e.push("#define "+t+" "+n)}return e.join(`
`)}function vE(i,e){const t={},n=i.getProgramParameter(e,i.ACTIVE_ATTRIBUTES);for(let s=0;s<n;s++){const r=i.getActiveAttrib(e,s),o=r.name;let a=1;r.type===i.FLOAT_MAT2&&(a=2),r.type===i.FLOAT_MAT3&&(a=3),r.type===i.FLOAT_MAT4&&(a=4),t[o]={type:r.type,location:i.getAttribLocation(e,o),locationSize:a}}return t}function hr(i){return i!==""}function jh(i,e){const t=e.numSpotLightShadows+e.numSpotLightMaps-e.numSpotLightShadowsWithMaps;return i.replace(/NUM_DIR_LIGHTS/g,e.numDirLights).replace(/NUM_SPOT_LIGHTS/g,e.numSpotLights).replace(/NUM_SPOT_LIGHT_MAPS/g,e.numSpotLightMaps).replace(/NUM_SPOT_LIGHT_COORDS/g,t).replace(/NUM_RECT_AREA_LIGHTS/g,e.numRectAreaLights).replace(/NUM_POINT_LIGHTS/g,e.numPointLights).replace(/NUM_HEMI_LIGHTS/g,e.numHemiLights).replace(/NUM_DIR_LIGHT_SHADOWS/g,e.numDirLightShadows).replace(/NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS/g,e.numSpotLightShadowsWithMaps).replace(/NUM_SPOT_LIGHT_SHADOWS/g,e.numSpotLightShadows).replace(/NUM_POINT_LIGHT_SHADOWS/g,e.numPointLightShadows)}function Kh(i,e){return i.replace(/NUM_CLIPPING_PLANES/g,e.numClippingPlanes).replace(/UNION_CLIPPING_PLANES/g,e.numClippingPlanes-e.numClipIntersection)}const xE=/^[ \t]*#include +<([\w\d./]+)>/gm;function Wc(i){return i.replace(xE,SE)}const yE=new Map([["encodings_fragment","colorspace_fragment"],["encodings_pars_fragment","colorspace_pars_fragment"],["output_fragment","opaque_fragment"]]);function SE(i,e){let t=Xe[e];if(t===void 0){const n=yE.get(e);if(n!==void 0)t=Xe[n],console.warn('THREE.WebGLRenderer: Shader chunk "%s" has been deprecated. Use "%s" instead.',e,n);else throw new Error("Can not resolve #include <"+e+">")}return Wc(t)}const ME=/#pragma unroll_loop_start\s+for\s*\(\s*int\s+i\s*=\s*(\d+)\s*;\s*i\s*<\s*(\d+)\s*;\s*i\s*\+\+\s*\)\s*{([\s\S]+?)}\s+#pragma unroll_loop_end/g;function Zh(i){return i.replace(ME,EE)}function EE(i,e,t,n){let s="";for(let r=parseInt(e);r<parseInt(t);r++)s+=n.replace(/\[\s*i\s*\]/g,"[ "+r+" ]").replace(/UNROLLED_LOOP_INDEX/g,r);return s}function Jh(i){let e="precision "+i.precision+` float;
precision `+i.precision+" int;";return i.precision==="highp"?e+=`
#define HIGH_PRECISION`:i.precision==="mediump"?e+=`
#define MEDIUM_PRECISION`:i.precision==="lowp"&&(e+=`
#define LOW_PRECISION`),e}function bE(i){let e="SHADOWMAP_TYPE_BASIC";return i.shadowMapType===Bp?e="SHADOWMAP_TYPE_PCF":i.shadowMapType===Z0?e="SHADOWMAP_TYPE_PCF_SOFT":i.shadowMapType===gi&&(e="SHADOWMAP_TYPE_VSM"),e}function TE(i){let e="ENVMAP_TYPE_CUBE";if(i.envMap)switch(i.envMapMode){case Rr:case Cr:e="ENVMAP_TYPE_CUBE";break;case pl:e="ENVMAP_TYPE_CUBE_UV";break}return e}function AE(i){let e="ENVMAP_MODE_REFLECTION";if(i.envMap)switch(i.envMapMode){case Cr:e="ENVMAP_MODE_REFRACTION";break}return e}function wE(i){let e="ENVMAP_BLENDING_NONE";if(i.envMap)switch(i.combine){case kp:e="ENVMAP_BLENDING_MULTIPLY";break;case Sv:e="ENVMAP_BLENDING_MIX";break;case Mv:e="ENVMAP_BLENDING_ADD";break}return e}function RE(i){const e=i.envMapCubeUVHeight;if(e===null)return null;const t=Math.log2(e)-2,n=1/e;return{texelWidth:1/(3*Math.max(Math.pow(2,t),7*16)),texelHeight:n,maxMip:t}}function CE(i,e,t,n){const s=i.getContext(),r=t.defines;let o=t.vertexShader,a=t.fragmentShader;const l=bE(t),c=TE(t),u=AE(t),f=wE(t),h=RE(t),d=t.isWebGL2?"":mE(t),g=_E(t),_=gE(r),m=s.createProgram();let p,x,y=t.glslVersion?"#version "+t.glslVersion+`
`:"";t.isRawShaderMaterial?(p=["#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,_].filter(hr).join(`
`),p.length>0&&(p+=`
`),x=[d,"#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,_].filter(hr).join(`
`),x.length>0&&(x+=`
`)):(p=[Jh(t),"#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,_,t.extensionClipCullDistance?"#define USE_CLIP_DISTANCE":"",t.batching?"#define USE_BATCHING":"",t.instancing?"#define USE_INSTANCING":"",t.instancingColor?"#define USE_INSTANCING_COLOR":"",t.useFog&&t.fog?"#define USE_FOG":"",t.useFog&&t.fogExp2?"#define FOG_EXP2":"",t.map?"#define USE_MAP":"",t.envMap?"#define USE_ENVMAP":"",t.envMap?"#define "+u:"",t.lightMap?"#define USE_LIGHTMAP":"",t.aoMap?"#define USE_AOMAP":"",t.bumpMap?"#define USE_BUMPMAP":"",t.normalMap?"#define USE_NORMALMAP":"",t.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",t.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",t.displacementMap?"#define USE_DISPLACEMENTMAP":"",t.emissiveMap?"#define USE_EMISSIVEMAP":"",t.anisotropy?"#define USE_ANISOTROPY":"",t.anisotropyMap?"#define USE_ANISOTROPYMAP":"",t.clearcoatMap?"#define USE_CLEARCOATMAP":"",t.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",t.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",t.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",t.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",t.specularMap?"#define USE_SPECULARMAP":"",t.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",t.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",t.roughnessMap?"#define USE_ROUGHNESSMAP":"",t.metalnessMap?"#define USE_METALNESSMAP":"",t.alphaMap?"#define USE_ALPHAMAP":"",t.alphaHash?"#define USE_ALPHAHASH":"",t.transmission?"#define USE_TRANSMISSION":"",t.transmissionMap?"#define USE_TRANSMISSIONMAP":"",t.thicknessMap?"#define USE_THICKNESSMAP":"",t.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",t.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",t.mapUv?"#define MAP_UV "+t.mapUv:"",t.alphaMapUv?"#define ALPHAMAP_UV "+t.alphaMapUv:"",t.lightMapUv?"#define LIGHTMAP_UV "+t.lightMapUv:"",t.aoMapUv?"#define AOMAP_UV "+t.aoMapUv:"",t.emissiveMapUv?"#define EMISSIVEMAP_UV "+t.emissiveMapUv:"",t.bumpMapUv?"#define BUMPMAP_UV "+t.bumpMapUv:"",t.normalMapUv?"#define NORMALMAP_UV "+t.normalMapUv:"",t.displacementMapUv?"#define DISPLACEMENTMAP_UV "+t.displacementMapUv:"",t.metalnessMapUv?"#define METALNESSMAP_UV "+t.metalnessMapUv:"",t.roughnessMapUv?"#define ROUGHNESSMAP_UV "+t.roughnessMapUv:"",t.anisotropyMapUv?"#define ANISOTROPYMAP_UV "+t.anisotropyMapUv:"",t.clearcoatMapUv?"#define CLEARCOATMAP_UV "+t.clearcoatMapUv:"",t.clearcoatNormalMapUv?"#define CLEARCOAT_NORMALMAP_UV "+t.clearcoatNormalMapUv:"",t.clearcoatRoughnessMapUv?"#define CLEARCOAT_ROUGHNESSMAP_UV "+t.clearcoatRoughnessMapUv:"",t.iridescenceMapUv?"#define IRIDESCENCEMAP_UV "+t.iridescenceMapUv:"",t.iridescenceThicknessMapUv?"#define IRIDESCENCE_THICKNESSMAP_UV "+t.iridescenceThicknessMapUv:"",t.sheenColorMapUv?"#define SHEEN_COLORMAP_UV "+t.sheenColorMapUv:"",t.sheenRoughnessMapUv?"#define SHEEN_ROUGHNESSMAP_UV "+t.sheenRoughnessMapUv:"",t.specularMapUv?"#define SPECULARMAP_UV "+t.specularMapUv:"",t.specularColorMapUv?"#define SPECULAR_COLORMAP_UV "+t.specularColorMapUv:"",t.specularIntensityMapUv?"#define SPECULAR_INTENSITYMAP_UV "+t.specularIntensityMapUv:"",t.transmissionMapUv?"#define TRANSMISSIONMAP_UV "+t.transmissionMapUv:"",t.thicknessMapUv?"#define THICKNESSMAP_UV "+t.thicknessMapUv:"",t.vertexTangents&&t.flatShading===!1?"#define USE_TANGENT":"",t.vertexColors?"#define USE_COLOR":"",t.vertexAlphas?"#define USE_COLOR_ALPHA":"",t.vertexUv1s?"#define USE_UV1":"",t.vertexUv2s?"#define USE_UV2":"",t.vertexUv3s?"#define USE_UV3":"",t.pointsUvs?"#define USE_POINTS_UV":"",t.flatShading?"#define FLAT_SHADED":"",t.skinning?"#define USE_SKINNING":"",t.morphTargets?"#define USE_MORPHTARGETS":"",t.morphNormals&&t.flatShading===!1?"#define USE_MORPHNORMALS":"",t.morphColors&&t.isWebGL2?"#define USE_MORPHCOLORS":"",t.morphTargetsCount>0&&t.isWebGL2?"#define MORPHTARGETS_TEXTURE":"",t.morphTargetsCount>0&&t.isWebGL2?"#define MORPHTARGETS_TEXTURE_STRIDE "+t.morphTextureStride:"",t.morphTargetsCount>0&&t.isWebGL2?"#define MORPHTARGETS_COUNT "+t.morphTargetsCount:"",t.doubleSided?"#define DOUBLE_SIDED":"",t.flipSided?"#define FLIP_SIDED":"",t.shadowMapEnabled?"#define USE_SHADOWMAP":"",t.shadowMapEnabled?"#define "+l:"",t.sizeAttenuation?"#define USE_SIZEATTENUATION":"",t.numLightProbes>0?"#define USE_LIGHT_PROBES":"",t.useLegacyLights?"#define LEGACY_LIGHTS":"",t.logarithmicDepthBuffer?"#define USE_LOGDEPTHBUF":"",t.logarithmicDepthBuffer&&t.rendererExtensionFragDepth?"#define USE_LOGDEPTHBUF_EXT":"","uniform mat4 modelMatrix;","uniform mat4 modelViewMatrix;","uniform mat4 projectionMatrix;","uniform mat4 viewMatrix;","uniform mat3 normalMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;","#ifdef USE_INSTANCING","	attribute mat4 instanceMatrix;","#endif","#ifdef USE_INSTANCING_COLOR","	attribute vec3 instanceColor;","#endif","attribute vec3 position;","attribute vec3 normal;","attribute vec2 uv;","#ifdef USE_UV1","	attribute vec2 uv1;","#endif","#ifdef USE_UV2","	attribute vec2 uv2;","#endif","#ifdef USE_UV3","	attribute vec2 uv3;","#endif","#ifdef USE_TANGENT","	attribute vec4 tangent;","#endif","#if defined( USE_COLOR_ALPHA )","	attribute vec4 color;","#elif defined( USE_COLOR )","	attribute vec3 color;","#endif","#if ( defined( USE_MORPHTARGETS ) && ! defined( MORPHTARGETS_TEXTURE ) )","	attribute vec3 morphTarget0;","	attribute vec3 morphTarget1;","	attribute vec3 morphTarget2;","	attribute vec3 morphTarget3;","	#ifdef USE_MORPHNORMALS","		attribute vec3 morphNormal0;","		attribute vec3 morphNormal1;","		attribute vec3 morphNormal2;","		attribute vec3 morphNormal3;","	#else","		attribute vec3 morphTarget4;","		attribute vec3 morphTarget5;","		attribute vec3 morphTarget6;","		attribute vec3 morphTarget7;","	#endif","#endif","#ifdef USE_SKINNING","	attribute vec4 skinIndex;","	attribute vec4 skinWeight;","#endif",`
`].filter(hr).join(`
`),x=[d,Jh(t),"#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,_,t.useFog&&t.fog?"#define USE_FOG":"",t.useFog&&t.fogExp2?"#define FOG_EXP2":"",t.map?"#define USE_MAP":"",t.matcap?"#define USE_MATCAP":"",t.envMap?"#define USE_ENVMAP":"",t.envMap?"#define "+c:"",t.envMap?"#define "+u:"",t.envMap?"#define "+f:"",h?"#define CUBEUV_TEXEL_WIDTH "+h.texelWidth:"",h?"#define CUBEUV_TEXEL_HEIGHT "+h.texelHeight:"",h?"#define CUBEUV_MAX_MIP "+h.maxMip+".0":"",t.lightMap?"#define USE_LIGHTMAP":"",t.aoMap?"#define USE_AOMAP":"",t.bumpMap?"#define USE_BUMPMAP":"",t.normalMap?"#define USE_NORMALMAP":"",t.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",t.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",t.emissiveMap?"#define USE_EMISSIVEMAP":"",t.anisotropy?"#define USE_ANISOTROPY":"",t.anisotropyMap?"#define USE_ANISOTROPYMAP":"",t.clearcoat?"#define USE_CLEARCOAT":"",t.clearcoatMap?"#define USE_CLEARCOATMAP":"",t.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",t.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",t.iridescence?"#define USE_IRIDESCENCE":"",t.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",t.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",t.specularMap?"#define USE_SPECULARMAP":"",t.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",t.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",t.roughnessMap?"#define USE_ROUGHNESSMAP":"",t.metalnessMap?"#define USE_METALNESSMAP":"",t.alphaMap?"#define USE_ALPHAMAP":"",t.alphaTest?"#define USE_ALPHATEST":"",t.alphaHash?"#define USE_ALPHAHASH":"",t.sheen?"#define USE_SHEEN":"",t.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",t.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",t.transmission?"#define USE_TRANSMISSION":"",t.transmissionMap?"#define USE_TRANSMISSIONMAP":"",t.thicknessMap?"#define USE_THICKNESSMAP":"",t.vertexTangents&&t.flatShading===!1?"#define USE_TANGENT":"",t.vertexColors||t.instancingColor?"#define USE_COLOR":"",t.vertexAlphas?"#define USE_COLOR_ALPHA":"",t.vertexUv1s?"#define USE_UV1":"",t.vertexUv2s?"#define USE_UV2":"",t.vertexUv3s?"#define USE_UV3":"",t.pointsUvs?"#define USE_POINTS_UV":"",t.gradientMap?"#define USE_GRADIENTMAP":"",t.flatShading?"#define FLAT_SHADED":"",t.doubleSided?"#define DOUBLE_SIDED":"",t.flipSided?"#define FLIP_SIDED":"",t.shadowMapEnabled?"#define USE_SHADOWMAP":"",t.shadowMapEnabled?"#define "+l:"",t.premultipliedAlpha?"#define PREMULTIPLIED_ALPHA":"",t.numLightProbes>0?"#define USE_LIGHT_PROBES":"",t.useLegacyLights?"#define LEGACY_LIGHTS":"",t.decodeVideoTexture?"#define DECODE_VIDEO_TEXTURE":"",t.logarithmicDepthBuffer?"#define USE_LOGDEPTHBUF":"",t.logarithmicDepthBuffer&&t.rendererExtensionFragDepth?"#define USE_LOGDEPTHBUF_EXT":"","uniform mat4 viewMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;",t.toneMapping!==Qi?"#define TONE_MAPPING":"",t.toneMapping!==Qi?Xe.tonemapping_pars_fragment:"",t.toneMapping!==Qi?pE("toneMapping",t.toneMapping):"",t.dithering?"#define DITHERING":"",t.opaque?"#define OPAQUE":"",Xe.colorspace_pars_fragment,dE("linearToOutputTexel",t.outputColorSpace),t.useDepthPacking?"#define DEPTH_PACKING "+t.depthPacking:"",`
`].filter(hr).join(`
`)),o=Wc(o),o=jh(o,t),o=Kh(o,t),a=Wc(a),a=jh(a,t),a=Kh(a,t),o=Zh(o),a=Zh(a),t.isWebGL2&&t.isRawShaderMaterial!==!0&&(y=`#version 300 es
`,p=[g,"precision mediump sampler2DArray;","#define attribute in","#define varying out","#define texture2D texture"].join(`
`)+`
`+p,x=["precision mediump sampler2DArray;","#define varying in",t.glslVersion===_h?"":"layout(location = 0) out highp vec4 pc_fragColor;",t.glslVersion===_h?"":"#define gl_FragColor pc_fragColor","#define gl_FragDepthEXT gl_FragDepth","#define texture2D texture","#define textureCube texture","#define texture2DProj textureProj","#define texture2DLodEXT textureLod","#define texture2DProjLodEXT textureProjLod","#define textureCubeLodEXT textureLod","#define texture2DGradEXT textureGrad","#define texture2DProjGradEXT textureProjGrad","#define textureCubeGradEXT textureGrad"].join(`
`)+`
`+x);const S=y+p+o,R=y+x+a,L=Yh(s,s.VERTEX_SHADER,S),w=Yh(s,s.FRAGMENT_SHADER,R);s.attachShader(m,L),s.attachShader(m,w),t.index0AttributeName!==void 0?s.bindAttribLocation(m,0,t.index0AttributeName):t.morphTargets===!0&&s.bindAttribLocation(m,0,"position"),s.linkProgram(m);function B(A){if(i.debug.checkShaderErrors){const I=s.getProgramInfoLog(m).trim(),O=s.getShaderInfoLog(L).trim(),k=s.getShaderInfoLog(w).trim();let H=!0,q=!0;if(s.getProgramParameter(m,s.LINK_STATUS)===!1)if(H=!1,typeof i.debug.onShaderError=="function")i.debug.onShaderError(s,m,L,w);else{const Z=$h(s,L,"vertex"),W=$h(s,w,"fragment");console.error("THREE.WebGLProgram: Shader Error "+s.getError()+" - VALIDATE_STATUS "+s.getProgramParameter(m,s.VALIDATE_STATUS)+`

Program Info Log: `+I+`
`+Z+`
`+W)}else I!==""?console.warn("THREE.WebGLProgram: Program Info Log:",I):(O===""||k==="")&&(q=!1);q&&(A.diagnostics={runnable:H,programLog:I,vertexShader:{log:O,prefix:p},fragmentShader:{log:k,prefix:x}})}s.deleteShader(L),s.deleteShader(w),v=new wa(s,m),b=vE(s,m)}let v;this.getUniforms=function(){return v===void 0&&B(this),v};let b;this.getAttributes=function(){return b===void 0&&B(this),b};let N=t.rendererExtensionParallelShaderCompile===!1;return this.isReady=function(){return N===!1&&(N=s.getProgramParameter(m,cE)),N},this.destroy=function(){n.releaseStatesOfProgram(this),s.deleteProgram(m),this.program=void 0},this.type=t.shaderType,this.name=t.shaderName,this.id=uE++,this.cacheKey=e,this.usedTimes=1,this.program=m,this.vertexShader=L,this.fragmentShader=w,this}let PE=0;class LE{constructor(){this.shaderCache=new Map,this.materialCache=new Map}update(e){const t=e.vertexShader,n=e.fragmentShader,s=this._getShaderStage(t),r=this._getShaderStage(n),o=this._getShaderCacheForMaterial(e);return o.has(s)===!1&&(o.add(s),s.usedTimes++),o.has(r)===!1&&(o.add(r),r.usedTimes++),this}remove(e){const t=this.materialCache.get(e);for(const n of t)n.usedTimes--,n.usedTimes===0&&this.shaderCache.delete(n.code);return this.materialCache.delete(e),this}getVertexShaderID(e){return this._getShaderStage(e.vertexShader).id}getFragmentShaderID(e){return this._getShaderStage(e.fragmentShader).id}dispose(){this.shaderCache.clear(),this.materialCache.clear()}_getShaderCacheForMaterial(e){const t=this.materialCache;let n=t.get(e);return n===void 0&&(n=new Set,t.set(e,n)),n}_getShaderStage(e){const t=this.shaderCache;let n=t.get(e);return n===void 0&&(n=new DE(e),t.set(e,n)),n}}class DE{constructor(e){this.id=PE++,this.code=e,this.usedTimes=0}}function UE(i,e,t,n,s,r,o){const a=new wu,l=new LE,c=[],u=s.isWebGL2,f=s.logarithmicDepthBuffer,h=s.vertexTextures;let d=s.precision;const g={MeshDepthMaterial:"depth",MeshDistanceMaterial:"distanceRGBA",MeshNormalMaterial:"normal",MeshBasicMaterial:"basic",MeshLambertMaterial:"lambert",MeshPhongMaterial:"phong",MeshToonMaterial:"toon",MeshStandardMaterial:"physical",MeshPhysicalMaterial:"physical",MeshMatcapMaterial:"matcap",LineBasicMaterial:"basic",LineDashedMaterial:"dashed",PointsMaterial:"points",ShadowMaterial:"shadow",SpriteMaterial:"sprite"};function _(v){return v===0?"uv":`uv${v}`}function m(v,b,N,A,I){const O=A.fog,k=I.geometry,H=v.isMeshStandardMaterial?A.environment:null,q=(v.isMeshStandardMaterial?t:e).get(v.envMap||H),Z=q&&q.mapping===pl?q.image.height:null,W=g[v.type];v.precision!==null&&(d=s.getMaxPrecision(v.precision),d!==v.precision&&console.warn("THREE.WebGLProgram.getParameters:",v.precision,"not supported, using",d,"instead."));const j=k.morphAttributes.position||k.morphAttributes.normal||k.morphAttributes.color,G=j!==void 0?j.length:0;let re=0;k.morphAttributes.position!==void 0&&(re=1),k.morphAttributes.normal!==void 0&&(re=2),k.morphAttributes.color!==void 0&&(re=3);let Q,le,_e,be;if(W){const Tt=ti[W];Q=Tt.vertexShader,le=Tt.fragmentShader}else Q=v.vertexShader,le=v.fragmentShader,l.update(v),_e=l.getVertexShaderID(v),be=l.getFragmentShaderID(v);const Te=i.getRenderTarget(),Ue=I.isInstancedMesh===!0,Ie=I.isBatchedMesh===!0,Se=!!v.map,Ke=!!v.matcap,E=!!q,z=!!v.aoMap,V=!!v.lightMap,te=!!v.bumpMap,K=!!v.normalMap,oe=!!v.displacementMap,ae=!!v.emissiveMap,T=!!v.metalnessMap,M=!!v.roughnessMap,U=v.anisotropy>0,ee=v.clearcoat>0,X=v.iridescence>0,J=v.sheen>0,fe=v.transmission>0,ue=U&&!!v.anisotropyMap,de=ee&&!!v.clearcoatMap,xe=ee&&!!v.clearcoatNormalMap,Ae=ee&&!!v.clearcoatRoughnessMap,ce=X&&!!v.iridescenceMap,ke=X&&!!v.iridescenceThicknessMap,De=J&&!!v.sheenColorMap,Le=J&&!!v.sheenRoughnessMap,Re=!!v.specularMap,ge=!!v.specularColorMap,D=!!v.specularIntensityMap,pe=fe&&!!v.transmissionMap,we=fe&&!!v.thicknessMap,Ee=!!v.gradientMap,he=!!v.alphaMap,F=v.alphaTest>0,me=!!v.alphaHash,ye=!!v.extensions,Oe=!!k.attributes.uv1,Pe=!!k.attributes.uv2,Ze=!!k.attributes.uv3;let Je=Qi;return v.toneMapped&&(Te===null||Te.isXRRenderTarget===!0)&&(Je=i.toneMapping),{isWebGL2:u,shaderID:W,shaderType:v.type,shaderName:v.name,vertexShader:Q,fragmentShader:le,defines:v.defines,customVertexShaderID:_e,customFragmentShaderID:be,isRawShaderMaterial:v.isRawShaderMaterial===!0,glslVersion:v.glslVersion,precision:d,batching:Ie,instancing:Ue,instancingColor:Ue&&I.instanceColor!==null,supportsVertexTextures:h,outputColorSpace:Te===null?i.outputColorSpace:Te.isXRRenderTarget===!0?Te.texture.colorSpace:Di,map:Se,matcap:Ke,envMap:E,envMapMode:E&&q.mapping,envMapCubeUVHeight:Z,aoMap:z,lightMap:V,bumpMap:te,normalMap:K,displacementMap:h&&oe,emissiveMap:ae,normalMapObjectSpace:K&&v.normalMapType===Vv,normalMapTangentSpace:K&&v.normalMapType===kv,metalnessMap:T,roughnessMap:M,anisotropy:U,anisotropyMap:ue,clearcoat:ee,clearcoatMap:de,clearcoatNormalMap:xe,clearcoatRoughnessMap:Ae,iridescence:X,iridescenceMap:ce,iridescenceThicknessMap:ke,sheen:J,sheenColorMap:De,sheenRoughnessMap:Le,specularMap:Re,specularColorMap:ge,specularIntensityMap:D,transmission:fe,transmissionMap:pe,thicknessMap:we,gradientMap:Ee,opaque:v.transparent===!1&&v.blending===Ji,alphaMap:he,alphaTest:F,alphaHash:me,combine:v.combine,mapUv:Se&&_(v.map.channel),aoMapUv:z&&_(v.aoMap.channel),lightMapUv:V&&_(v.lightMap.channel),bumpMapUv:te&&_(v.bumpMap.channel),normalMapUv:K&&_(v.normalMap.channel),displacementMapUv:oe&&_(v.displacementMap.channel),emissiveMapUv:ae&&_(v.emissiveMap.channel),metalnessMapUv:T&&_(v.metalnessMap.channel),roughnessMapUv:M&&_(v.roughnessMap.channel),anisotropyMapUv:ue&&_(v.anisotropyMap.channel),clearcoatMapUv:de&&_(v.clearcoatMap.channel),clearcoatNormalMapUv:xe&&_(v.clearcoatNormalMap.channel),clearcoatRoughnessMapUv:Ae&&_(v.clearcoatRoughnessMap.channel),iridescenceMapUv:ce&&_(v.iridescenceMap.channel),iridescenceThicknessMapUv:ke&&_(v.iridescenceThicknessMap.channel),sheenColorMapUv:De&&_(v.sheenColorMap.channel),sheenRoughnessMapUv:Le&&_(v.sheenRoughnessMap.channel),specularMapUv:Re&&_(v.specularMap.channel),specularColorMapUv:ge&&_(v.specularColorMap.channel),specularIntensityMapUv:D&&_(v.specularIntensityMap.channel),transmissionMapUv:pe&&_(v.transmissionMap.channel),thicknessMapUv:we&&_(v.thicknessMap.channel),alphaMapUv:he&&_(v.alphaMap.channel),vertexTangents:!!k.attributes.tangent&&(K||U),vertexColors:v.vertexColors,vertexAlphas:v.vertexColors===!0&&!!k.attributes.color&&k.attributes.color.itemSize===4,vertexUv1s:Oe,vertexUv2s:Pe,vertexUv3s:Ze,pointsUvs:I.isPoints===!0&&!!k.attributes.uv&&(Se||he),fog:!!O,useFog:v.fog===!0,fogExp2:O&&O.isFogExp2,flatShading:v.flatShading===!0,sizeAttenuation:v.sizeAttenuation===!0,logarithmicDepthBuffer:f,skinning:I.isSkinnedMesh===!0,morphTargets:k.morphAttributes.position!==void 0,morphNormals:k.morphAttributes.normal!==void 0,morphColors:k.morphAttributes.color!==void 0,morphTargetsCount:G,morphTextureStride:re,numDirLights:b.directional.length,numPointLights:b.point.length,numSpotLights:b.spot.length,numSpotLightMaps:b.spotLightMap.length,numRectAreaLights:b.rectArea.length,numHemiLights:b.hemi.length,numDirLightShadows:b.directionalShadowMap.length,numPointLightShadows:b.pointShadowMap.length,numSpotLightShadows:b.spotShadowMap.length,numSpotLightShadowsWithMaps:b.numSpotLightShadowsWithMaps,numLightProbes:b.numLightProbes,numClippingPlanes:o.numPlanes,numClipIntersection:o.numIntersection,dithering:v.dithering,shadowMapEnabled:i.shadowMap.enabled&&N.length>0,shadowMapType:i.shadowMap.type,toneMapping:Je,useLegacyLights:i._useLegacyLights,decodeVideoTexture:Se&&v.map.isVideoTexture===!0&&at.getTransfer(v.map.colorSpace)===mt,premultipliedAlpha:v.premultipliedAlpha,doubleSided:v.side===Ai,flipSided:v.side===un,useDepthPacking:v.depthPacking>=0,depthPacking:v.depthPacking||0,index0AttributeName:v.index0AttributeName,extensionDerivatives:ye&&v.extensions.derivatives===!0,extensionFragDepth:ye&&v.extensions.fragDepth===!0,extensionDrawBuffers:ye&&v.extensions.drawBuffers===!0,extensionShaderTextureLOD:ye&&v.extensions.shaderTextureLOD===!0,extensionClipCullDistance:ye&&v.extensions.clipCullDistance&&n.has("WEBGL_clip_cull_distance"),rendererExtensionFragDepth:u||n.has("EXT_frag_depth"),rendererExtensionDrawBuffers:u||n.has("WEBGL_draw_buffers"),rendererExtensionShaderTextureLod:u||n.has("EXT_shader_texture_lod"),rendererExtensionParallelShaderCompile:n.has("KHR_parallel_shader_compile"),customProgramCacheKey:v.customProgramCacheKey()}}function p(v){const b=[];if(v.shaderID?b.push(v.shaderID):(b.push(v.customVertexShaderID),b.push(v.customFragmentShaderID)),v.defines!==void 0)for(const N in v.defines)b.push(N),b.push(v.defines[N]);return v.isRawShaderMaterial===!1&&(x(b,v),y(b,v),b.push(i.outputColorSpace)),b.push(v.customProgramCacheKey),b.join()}function x(v,b){v.push(b.precision),v.push(b.outputColorSpace),v.push(b.envMapMode),v.push(b.envMapCubeUVHeight),v.push(b.mapUv),v.push(b.alphaMapUv),v.push(b.lightMapUv),v.push(b.aoMapUv),v.push(b.bumpMapUv),v.push(b.normalMapUv),v.push(b.displacementMapUv),v.push(b.emissiveMapUv),v.push(b.metalnessMapUv),v.push(b.roughnessMapUv),v.push(b.anisotropyMapUv),v.push(b.clearcoatMapUv),v.push(b.clearcoatNormalMapUv),v.push(b.clearcoatRoughnessMapUv),v.push(b.iridescenceMapUv),v.push(b.iridescenceThicknessMapUv),v.push(b.sheenColorMapUv),v.push(b.sheenRoughnessMapUv),v.push(b.specularMapUv),v.push(b.specularColorMapUv),v.push(b.specularIntensityMapUv),v.push(b.transmissionMapUv),v.push(b.thicknessMapUv),v.push(b.combine),v.push(b.fogExp2),v.push(b.sizeAttenuation),v.push(b.morphTargetsCount),v.push(b.morphAttributeCount),v.push(b.numDirLights),v.push(b.numPointLights),v.push(b.numSpotLights),v.push(b.numSpotLightMaps),v.push(b.numHemiLights),v.push(b.numRectAreaLights),v.push(b.numDirLightShadows),v.push(b.numPointLightShadows),v.push(b.numSpotLightShadows),v.push(b.numSpotLightShadowsWithMaps),v.push(b.numLightProbes),v.push(b.shadowMapType),v.push(b.toneMapping),v.push(b.numClippingPlanes),v.push(b.numClipIntersection),v.push(b.depthPacking)}function y(v,b){a.disableAll(),b.isWebGL2&&a.enable(0),b.supportsVertexTextures&&a.enable(1),b.instancing&&a.enable(2),b.instancingColor&&a.enable(3),b.matcap&&a.enable(4),b.envMap&&a.enable(5),b.normalMapObjectSpace&&a.enable(6),b.normalMapTangentSpace&&a.enable(7),b.clearcoat&&a.enable(8),b.iridescence&&a.enable(9),b.alphaTest&&a.enable(10),b.vertexColors&&a.enable(11),b.vertexAlphas&&a.enable(12),b.vertexUv1s&&a.enable(13),b.vertexUv2s&&a.enable(14),b.vertexUv3s&&a.enable(15),b.vertexTangents&&a.enable(16),b.anisotropy&&a.enable(17),b.alphaHash&&a.enable(18),b.batching&&a.enable(19),v.push(a.mask),a.disableAll(),b.fog&&a.enable(0),b.useFog&&a.enable(1),b.flatShading&&a.enable(2),b.logarithmicDepthBuffer&&a.enable(3),b.skinning&&a.enable(4),b.morphTargets&&a.enable(5),b.morphNormals&&a.enable(6),b.morphColors&&a.enable(7),b.premultipliedAlpha&&a.enable(8),b.shadowMapEnabled&&a.enable(9),b.useLegacyLights&&a.enable(10),b.doubleSided&&a.enable(11),b.flipSided&&a.enable(12),b.useDepthPacking&&a.enable(13),b.dithering&&a.enable(14),b.transmission&&a.enable(15),b.sheen&&a.enable(16),b.opaque&&a.enable(17),b.pointsUvs&&a.enable(18),b.decodeVideoTexture&&a.enable(19),v.push(a.mask)}function S(v){const b=g[v.type];let N;if(b){const A=ti[b];N=mx.clone(A.uniforms)}else N=v.uniforms;return N}function R(v,b){let N;for(let A=0,I=c.length;A<I;A++){const O=c[A];if(O.cacheKey===b){N=O,++N.usedTimes;break}}return N===void 0&&(N=new CE(i,b,v,r),c.push(N)),N}function L(v){if(--v.usedTimes===0){const b=c.indexOf(v);c[b]=c[c.length-1],c.pop(),v.destroy()}}function w(v){l.remove(v)}function B(){l.dispose()}return{getParameters:m,getProgramCacheKey:p,getUniforms:S,acquireProgram:R,releaseProgram:L,releaseShaderCache:w,programs:c,dispose:B}}function IE(){let i=new WeakMap;function e(r){let o=i.get(r);return o===void 0&&(o={},i.set(r,o)),o}function t(r){i.delete(r)}function n(r,o,a){i.get(r)[o]=a}function s(){i=new WeakMap}return{get:e,remove:t,update:n,dispose:s}}function OE(i,e){return i.groupOrder!==e.groupOrder?i.groupOrder-e.groupOrder:i.renderOrder!==e.renderOrder?i.renderOrder-e.renderOrder:i.material.id!==e.material.id?i.material.id-e.material.id:i.z!==e.z?i.z-e.z:i.id-e.id}function Qh(i,e){return i.groupOrder!==e.groupOrder?i.groupOrder-e.groupOrder:i.renderOrder!==e.renderOrder?i.renderOrder-e.renderOrder:i.z!==e.z?e.z-i.z:i.id-e.id}function ed(){const i=[];let e=0;const t=[],n=[],s=[];function r(){e=0,t.length=0,n.length=0,s.length=0}function o(f,h,d,g,_,m){let p=i[e];return p===void 0?(p={id:f.id,object:f,geometry:h,material:d,groupOrder:g,renderOrder:f.renderOrder,z:_,group:m},i[e]=p):(p.id=f.id,p.object=f,p.geometry=h,p.material=d,p.groupOrder=g,p.renderOrder=f.renderOrder,p.z=_,p.group=m),e++,p}function a(f,h,d,g,_,m){const p=o(f,h,d,g,_,m);d.transmission>0?n.push(p):d.transparent===!0?s.push(p):t.push(p)}function l(f,h,d,g,_,m){const p=o(f,h,d,g,_,m);d.transmission>0?n.unshift(p):d.transparent===!0?s.unshift(p):t.unshift(p)}function c(f,h){t.length>1&&t.sort(f||OE),n.length>1&&n.sort(h||Qh),s.length>1&&s.sort(h||Qh)}function u(){for(let f=e,h=i.length;f<h;f++){const d=i[f];if(d.id===null)break;d.id=null,d.object=null,d.geometry=null,d.material=null,d.group=null}}return{opaque:t,transmissive:n,transparent:s,init:r,push:a,unshift:l,finish:u,sort:c}}function NE(){let i=new WeakMap;function e(n,s){const r=i.get(n);let o;return r===void 0?(o=new ed,i.set(n,[o])):s>=r.length?(o=new ed,r.push(o)):o=r[s],o}function t(){i=new WeakMap}return{get:e,dispose:t}}function FE(){const i={};return{get:function(e){if(i[e.id]!==void 0)return i[e.id];let t;switch(e.type){case"DirectionalLight":t={direction:new $,color:new Qe};break;case"SpotLight":t={position:new $,direction:new $,color:new Qe,distance:0,coneCos:0,penumbraCos:0,decay:0};break;case"PointLight":t={position:new $,color:new Qe,distance:0,decay:0};break;case"HemisphereLight":t={direction:new $,skyColor:new Qe,groundColor:new Qe};break;case"RectAreaLight":t={color:new Qe,position:new $,halfWidth:new $,halfHeight:new $};break}return i[e.id]=t,t}}}function zE(){const i={};return{get:function(e){if(i[e.id]!==void 0)return i[e.id];let t;switch(e.type){case"DirectionalLight":t={shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new He};break;case"SpotLight":t={shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new He};break;case"PointLight":t={shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new He,shadowCameraNear:1,shadowCameraFar:1e3};break}return i[e.id]=t,t}}}let BE=0;function kE(i,e){return(e.castShadow?2:0)-(i.castShadow?2:0)+(e.map?1:0)-(i.map?1:0)}function VE(i,e){const t=new FE,n=zE(),s={version:0,hash:{directionalLength:-1,pointLength:-1,spotLength:-1,rectAreaLength:-1,hemiLength:-1,numDirectionalShadows:-1,numPointShadows:-1,numSpotShadows:-1,numSpotMaps:-1,numLightProbes:-1},ambient:[0,0,0],probe:[],directional:[],directionalShadow:[],directionalShadowMap:[],directionalShadowMatrix:[],spot:[],spotLightMap:[],spotShadow:[],spotShadowMap:[],spotLightMatrix:[],rectArea:[],rectAreaLTC1:null,rectAreaLTC2:null,point:[],pointShadow:[],pointShadowMap:[],pointShadowMatrix:[],hemi:[],numSpotLightShadowsWithMaps:0,numLightProbes:0};for(let u=0;u<9;u++)s.probe.push(new $);const r=new $,o=new Lt,a=new Lt;function l(u,f){let h=0,d=0,g=0;for(let A=0;A<9;A++)s.probe[A].set(0,0,0);let _=0,m=0,p=0,x=0,y=0,S=0,R=0,L=0,w=0,B=0,v=0;u.sort(kE);const b=f===!0?Math.PI:1;for(let A=0,I=u.length;A<I;A++){const O=u[A],k=O.color,H=O.intensity,q=O.distance,Z=O.shadow&&O.shadow.map?O.shadow.map.texture:null;if(O.isAmbientLight)h+=k.r*H*b,d+=k.g*H*b,g+=k.b*H*b;else if(O.isLightProbe){for(let W=0;W<9;W++)s.probe[W].addScaledVector(O.sh.coefficients[W],H);v++}else if(O.isDirectionalLight){const W=t.get(O);if(W.color.copy(O.color).multiplyScalar(O.intensity*b),O.castShadow){const j=O.shadow,G=n.get(O);G.shadowBias=j.bias,G.shadowNormalBias=j.normalBias,G.shadowRadius=j.radius,G.shadowMapSize=j.mapSize,s.directionalShadow[_]=G,s.directionalShadowMap[_]=Z,s.directionalShadowMatrix[_]=O.shadow.matrix,S++}s.directional[_]=W,_++}else if(O.isSpotLight){const W=t.get(O);W.position.setFromMatrixPosition(O.matrixWorld),W.color.copy(k).multiplyScalar(H*b),W.distance=q,W.coneCos=Math.cos(O.angle),W.penumbraCos=Math.cos(O.angle*(1-O.penumbra)),W.decay=O.decay,s.spot[p]=W;const j=O.shadow;if(O.map&&(s.spotLightMap[w]=O.map,w++,j.updateMatrices(O),O.castShadow&&B++),s.spotLightMatrix[p]=j.matrix,O.castShadow){const G=n.get(O);G.shadowBias=j.bias,G.shadowNormalBias=j.normalBias,G.shadowRadius=j.radius,G.shadowMapSize=j.mapSize,s.spotShadow[p]=G,s.spotShadowMap[p]=Z,L++}p++}else if(O.isRectAreaLight){const W=t.get(O);W.color.copy(k).multiplyScalar(H),W.halfWidth.set(O.width*.5,0,0),W.halfHeight.set(0,O.height*.5,0),s.rectArea[x]=W,x++}else if(O.isPointLight){const W=t.get(O);if(W.color.copy(O.color).multiplyScalar(O.intensity*b),W.distance=O.distance,W.decay=O.decay,O.castShadow){const j=O.shadow,G=n.get(O);G.shadowBias=j.bias,G.shadowNormalBias=j.normalBias,G.shadowRadius=j.radius,G.shadowMapSize=j.mapSize,G.shadowCameraNear=j.camera.near,G.shadowCameraFar=j.camera.far,s.pointShadow[m]=G,s.pointShadowMap[m]=Z,s.pointShadowMatrix[m]=O.shadow.matrix,R++}s.point[m]=W,m++}else if(O.isHemisphereLight){const W=t.get(O);W.skyColor.copy(O.color).multiplyScalar(H*b),W.groundColor.copy(O.groundColor).multiplyScalar(H*b),s.hemi[y]=W,y++}}x>0&&(e.isWebGL2?i.has("OES_texture_float_linear")===!0?(s.rectAreaLTC1=ve.LTC_FLOAT_1,s.rectAreaLTC2=ve.LTC_FLOAT_2):(s.rectAreaLTC1=ve.LTC_HALF_1,s.rectAreaLTC2=ve.LTC_HALF_2):i.has("OES_texture_float_linear")===!0?(s.rectAreaLTC1=ve.LTC_FLOAT_1,s.rectAreaLTC2=ve.LTC_FLOAT_2):i.has("OES_texture_half_float_linear")===!0?(s.rectAreaLTC1=ve.LTC_HALF_1,s.rectAreaLTC2=ve.LTC_HALF_2):console.error("THREE.WebGLRenderer: Unable to use RectAreaLight. Missing WebGL extensions.")),s.ambient[0]=h,s.ambient[1]=d,s.ambient[2]=g;const N=s.hash;(N.directionalLength!==_||N.pointLength!==m||N.spotLength!==p||N.rectAreaLength!==x||N.hemiLength!==y||N.numDirectionalShadows!==S||N.numPointShadows!==R||N.numSpotShadows!==L||N.numSpotMaps!==w||N.numLightProbes!==v)&&(s.directional.length=_,s.spot.length=p,s.rectArea.length=x,s.point.length=m,s.hemi.length=y,s.directionalShadow.length=S,s.directionalShadowMap.length=S,s.pointShadow.length=R,s.pointShadowMap.length=R,s.spotShadow.length=L,s.spotShadowMap.length=L,s.directionalShadowMatrix.length=S,s.pointShadowMatrix.length=R,s.spotLightMatrix.length=L+w-B,s.spotLightMap.length=w,s.numSpotLightShadowsWithMaps=B,s.numLightProbes=v,N.directionalLength=_,N.pointLength=m,N.spotLength=p,N.rectAreaLength=x,N.hemiLength=y,N.numDirectionalShadows=S,N.numPointShadows=R,N.numSpotShadows=L,N.numSpotMaps=w,N.numLightProbes=v,s.version=BE++)}function c(u,f){let h=0,d=0,g=0,_=0,m=0;const p=f.matrixWorldInverse;for(let x=0,y=u.length;x<y;x++){const S=u[x];if(S.isDirectionalLight){const R=s.directional[h];R.direction.setFromMatrixPosition(S.matrixWorld),r.setFromMatrixPosition(S.target.matrixWorld),R.direction.sub(r),R.direction.transformDirection(p),h++}else if(S.isSpotLight){const R=s.spot[g];R.position.setFromMatrixPosition(S.matrixWorld),R.position.applyMatrix4(p),R.direction.setFromMatrixPosition(S.matrixWorld),r.setFromMatrixPosition(S.target.matrixWorld),R.direction.sub(r),R.direction.transformDirection(p),g++}else if(S.isRectAreaLight){const R=s.rectArea[_];R.position.setFromMatrixPosition(S.matrixWorld),R.position.applyMatrix4(p),a.identity(),o.copy(S.matrixWorld),o.premultiply(p),a.extractRotation(o),R.halfWidth.set(S.width*.5,0,0),R.halfHeight.set(0,S.height*.5,0),R.halfWidth.applyMatrix4(a),R.halfHeight.applyMatrix4(a),_++}else if(S.isPointLight){const R=s.point[d];R.position.setFromMatrixPosition(S.matrixWorld),R.position.applyMatrix4(p),d++}else if(S.isHemisphereLight){const R=s.hemi[m];R.direction.setFromMatrixPosition(S.matrixWorld),R.direction.transformDirection(p),m++}}}return{setup:l,setupView:c,state:s}}function td(i,e){const t=new VE(i,e),n=[],s=[];function r(){n.length=0,s.length=0}function o(f){n.push(f)}function a(f){s.push(f)}function l(f){t.setup(n,f)}function c(f){t.setupView(n,f)}return{init:r,state:{lightsArray:n,shadowsArray:s,lights:t},setupLights:l,setupLightsView:c,pushLight:o,pushShadow:a}}function HE(i,e){let t=new WeakMap;function n(r,o=0){const a=t.get(r);let l;return a===void 0?(l=new td(i,e),t.set(r,[l])):o>=a.length?(l=new td(i,e),a.push(l)):l=a[o],l}function s(){t=new WeakMap}return{get:n,dispose:s}}class GE extends No{constructor(e){super(),this.isMeshDepthMaterial=!0,this.type="MeshDepthMaterial",this.depthPacking=zv,this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.wireframe=!1,this.wireframeLinewidth=1,this.setValues(e)}copy(e){return super.copy(e),this.depthPacking=e.depthPacking,this.map=e.map,this.alphaMap=e.alphaMap,this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this}}class WE extends No{constructor(e){super(),this.isMeshDistanceMaterial=!0,this.type="MeshDistanceMaterial",this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.setValues(e)}copy(e){return super.copy(e),this.map=e.map,this.alphaMap=e.alphaMap,this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this}}const XE=`void main() {
	gl_Position = vec4( position, 1.0 );
}`,qE=`uniform sampler2D shadow_pass;
uniform vec2 resolution;
uniform float radius;
#include <packing>
void main() {
	const float samples = float( VSM_SAMPLES );
	float mean = 0.0;
	float squared_mean = 0.0;
	float uvStride = samples <= 1.0 ? 0.0 : 2.0 / ( samples - 1.0 );
	float uvStart = samples <= 1.0 ? 0.0 : - 1.0;
	for ( float i = 0.0; i < samples; i ++ ) {
		float uvOffset = uvStart + i * uvStride;
		#ifdef HORIZONTAL_PASS
			vec2 distribution = unpackRGBATo2Half( texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( uvOffset, 0.0 ) * radius ) / resolution ) );
			mean += distribution.x;
			squared_mean += distribution.y * distribution.y + distribution.x * distribution.x;
		#else
			float depth = unpackRGBAToDepth( texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( 0.0, uvOffset ) * radius ) / resolution ) );
			mean += depth;
			squared_mean += depth * depth;
		#endif
	}
	mean = mean / samples;
	squared_mean = squared_mean / samples;
	float std_dev = sqrt( squared_mean - mean * mean );
	gl_FragColor = pack2HalfToRGBA( vec2( mean, std_dev ) );
}`;function YE(i,e,t){let n=new Ru;const s=new He,r=new He,o=new Ft,a=new GE({depthPacking:Bv}),l=new WE,c={},u=t.maxTextureSize,f={[ss]:un,[un]:ss,[Ai]:Ai},h=new rs({defines:{VSM_SAMPLES:8},uniforms:{shadow_pass:{value:null},resolution:{value:new He},radius:{value:4}},vertexShader:XE,fragmentShader:qE}),d=h.clone();d.defines.HORIZONTAL_PASS=1;const g=new Ni;g.setAttribute("position",new Bn(new Float32Array([-1,-1,.5,3,-1,.5,-1,3,.5]),3));const _=new Yi(g,h),m=this;this.enabled=!1,this.autoUpdate=!0,this.needsUpdate=!1,this.type=Bp;let p=this.type;this.render=function(L,w,B){if(m.enabled===!1||m.autoUpdate===!1&&m.needsUpdate===!1||L.length===0)return;const v=i.getRenderTarget(),b=i.getActiveCubeFace(),N=i.getActiveMipmapLevel(),A=i.state;A.setBlending(Zi),A.buffers.color.setClear(1,1,1,1),A.buffers.depth.setTest(!0),A.setScissorTest(!1);const I=p!==gi&&this.type===gi,O=p===gi&&this.type!==gi;for(let k=0,H=L.length;k<H;k++){const q=L[k],Z=q.shadow;if(Z===void 0){console.warn("THREE.WebGLShadowMap:",q,"has no shadow.");continue}if(Z.autoUpdate===!1&&Z.needsUpdate===!1)continue;s.copy(Z.mapSize);const W=Z.getFrameExtents();if(s.multiply(W),r.copy(Z.mapSize),(s.x>u||s.y>u)&&(s.x>u&&(r.x=Math.floor(u/W.x),s.x=r.x*W.x,Z.mapSize.x=r.x),s.y>u&&(r.y=Math.floor(u/W.y),s.y=r.y*W.y,Z.mapSize.y=r.y)),Z.map===null||I===!0||O===!0){const G=this.type!==gi?{minFilter:tn,magFilter:tn}:{};Z.map!==null&&Z.map.dispose(),Z.map=new Bs(s.x,s.y,G),Z.map.texture.name=q.name+".shadowMap",Z.camera.updateProjectionMatrix()}i.setRenderTarget(Z.map),i.clear();const j=Z.getViewportCount();for(let G=0;G<j;G++){const re=Z.getViewport(G);o.set(r.x*re.x,r.y*re.y,r.x*re.z,r.y*re.w),A.viewport(o),Z.updateMatrices(q,G),n=Z.getFrustum(),S(w,B,Z.camera,q,this.type)}Z.isPointLightShadow!==!0&&this.type===gi&&x(Z,B),Z.needsUpdate=!1}p=this.type,m.needsUpdate=!1,i.setRenderTarget(v,b,N)};function x(L,w){const B=e.update(_);h.defines.VSM_SAMPLES!==L.blurSamples&&(h.defines.VSM_SAMPLES=L.blurSamples,d.defines.VSM_SAMPLES=L.blurSamples,h.needsUpdate=!0,d.needsUpdate=!0),L.mapPass===null&&(L.mapPass=new Bs(s.x,s.y)),h.uniforms.shadow_pass.value=L.map.texture,h.uniforms.resolution.value=L.mapSize,h.uniforms.radius.value=L.radius,i.setRenderTarget(L.mapPass),i.clear(),i.renderBufferDirect(w,null,B,h,_,null),d.uniforms.shadow_pass.value=L.mapPass.texture,d.uniforms.resolution.value=L.mapSize,d.uniforms.radius.value=L.radius,i.setRenderTarget(L.map),i.clear(),i.renderBufferDirect(w,null,B,d,_,null)}function y(L,w,B,v){let b=null;const N=B.isPointLight===!0?L.customDistanceMaterial:L.customDepthMaterial;if(N!==void 0)b=N;else if(b=B.isPointLight===!0?l:a,i.localClippingEnabled&&w.clipShadows===!0&&Array.isArray(w.clippingPlanes)&&w.clippingPlanes.length!==0||w.displacementMap&&w.displacementScale!==0||w.alphaMap&&w.alphaTest>0||w.map&&w.alphaTest>0){const A=b.uuid,I=w.uuid;let O=c[A];O===void 0&&(O={},c[A]=O);let k=O[I];k===void 0&&(k=b.clone(),O[I]=k,w.addEventListener("dispose",R)),b=k}if(b.visible=w.visible,b.wireframe=w.wireframe,v===gi?b.side=w.shadowSide!==null?w.shadowSide:w.side:b.side=w.shadowSide!==null?w.shadowSide:f[w.side],b.alphaMap=w.alphaMap,b.alphaTest=w.alphaTest,b.map=w.map,b.clipShadows=w.clipShadows,b.clippingPlanes=w.clippingPlanes,b.clipIntersection=w.clipIntersection,b.displacementMap=w.displacementMap,b.displacementScale=w.displacementScale,b.displacementBias=w.displacementBias,b.wireframeLinewidth=w.wireframeLinewidth,b.linewidth=w.linewidth,B.isPointLight===!0&&b.isMeshDistanceMaterial===!0){const A=i.properties.get(b);A.light=B}return b}function S(L,w,B,v,b){if(L.visible===!1)return;if(L.layers.test(w.layers)&&(L.isMesh||L.isLine||L.isPoints)&&(L.castShadow||L.receiveShadow&&b===gi)&&(!L.frustumCulled||n.intersectsObject(L))){L.modelViewMatrix.multiplyMatrices(B.matrixWorldInverse,L.matrixWorld);const I=e.update(L),O=L.material;if(Array.isArray(O)){const k=I.groups;for(let H=0,q=k.length;H<q;H++){const Z=k[H],W=O[Z.materialIndex];if(W&&W.visible){const j=y(L,W,v,b);L.onBeforeShadow(i,L,w,B,I,j,Z),i.renderBufferDirect(B,null,I,j,L,Z),L.onAfterShadow(i,L,w,B,I,j,Z)}}}else if(O.visible){const k=y(L,O,v,b);L.onBeforeShadow(i,L,w,B,I,k,null),i.renderBufferDirect(B,null,I,k,L,null),L.onAfterShadow(i,L,w,B,I,k,null)}}const A=L.children;for(let I=0,O=A.length;I<O;I++)S(A[I],w,B,v,b)}function R(L){L.target.removeEventListener("dispose",R);for(const B in c){const v=c[B],b=L.target.uuid;b in v&&(v[b].dispose(),delete v[b])}}}function $E(i,e,t){const n=t.isWebGL2;function s(){let F=!1;const me=new Ft;let ye=null;const Oe=new Ft(0,0,0,0);return{setMask:function(Pe){ye!==Pe&&!F&&(i.colorMask(Pe,Pe,Pe,Pe),ye=Pe)},setLocked:function(Pe){F=Pe},setClear:function(Pe,Ze,Je,St,Tt){Tt===!0&&(Pe*=St,Ze*=St,Je*=St),me.set(Pe,Ze,Je,St),Oe.equals(me)===!1&&(i.clearColor(Pe,Ze,Je,St),Oe.copy(me))},reset:function(){F=!1,ye=null,Oe.set(-1,0,0,0)}}}function r(){let F=!1,me=null,ye=null,Oe=null;return{setTest:function(Pe){Pe?Ie(i.DEPTH_TEST):Se(i.DEPTH_TEST)},setMask:function(Pe){me!==Pe&&!F&&(i.depthMask(Pe),me=Pe)},setFunc:function(Pe){if(ye!==Pe){switch(Pe){case pv:i.depthFunc(i.NEVER);break;case mv:i.depthFunc(i.ALWAYS);break;case _v:i.depthFunc(i.LESS);break;case Va:i.depthFunc(i.LEQUAL);break;case gv:i.depthFunc(i.EQUAL);break;case vv:i.depthFunc(i.GEQUAL);break;case xv:i.depthFunc(i.GREATER);break;case yv:i.depthFunc(i.NOTEQUAL);break;default:i.depthFunc(i.LEQUAL)}ye=Pe}},setLocked:function(Pe){F=Pe},setClear:function(Pe){Oe!==Pe&&(i.clearDepth(Pe),Oe=Pe)},reset:function(){F=!1,me=null,ye=null,Oe=null}}}function o(){let F=!1,me=null,ye=null,Oe=null,Pe=null,Ze=null,Je=null,St=null,Tt=null;return{setTest:function(nt){F||(nt?Ie(i.STENCIL_TEST):Se(i.STENCIL_TEST))},setMask:function(nt){me!==nt&&!F&&(i.stencilMask(nt),me=nt)},setFunc:function(nt,Rt,jn){(ye!==nt||Oe!==Rt||Pe!==jn)&&(i.stencilFunc(nt,Rt,jn),ye=nt,Oe=Rt,Pe=jn)},setOp:function(nt,Rt,jn){(Ze!==nt||Je!==Rt||St!==jn)&&(i.stencilOp(nt,Rt,jn),Ze=nt,Je=Rt,St=jn)},setLocked:function(nt){F=nt},setClear:function(nt){Tt!==nt&&(i.clearStencil(nt),Tt=nt)},reset:function(){F=!1,me=null,ye=null,Oe=null,Pe=null,Ze=null,Je=null,St=null,Tt=null}}}const a=new s,l=new r,c=new o,u=new WeakMap,f=new WeakMap;let h={},d={},g=new WeakMap,_=[],m=null,p=!1,x=null,y=null,S=null,R=null,L=null,w=null,B=null,v=new Qe(0,0,0),b=0,N=!1,A=null,I=null,O=null,k=null,H=null;const q=i.getParameter(i.MAX_COMBINED_TEXTURE_IMAGE_UNITS);let Z=!1,W=0;const j=i.getParameter(i.VERSION);j.indexOf("WebGL")!==-1?(W=parseFloat(/^WebGL (\d)/.exec(j)[1]),Z=W>=1):j.indexOf("OpenGL ES")!==-1&&(W=parseFloat(/^OpenGL ES (\d)/.exec(j)[1]),Z=W>=2);let G=null,re={};const Q=i.getParameter(i.SCISSOR_BOX),le=i.getParameter(i.VIEWPORT),_e=new Ft().fromArray(Q),be=new Ft().fromArray(le);function Te(F,me,ye,Oe){const Pe=new Uint8Array(4),Ze=i.createTexture();i.bindTexture(F,Ze),i.texParameteri(F,i.TEXTURE_MIN_FILTER,i.NEAREST),i.texParameteri(F,i.TEXTURE_MAG_FILTER,i.NEAREST);for(let Je=0;Je<ye;Je++)n&&(F===i.TEXTURE_3D||F===i.TEXTURE_2D_ARRAY)?i.texImage3D(me,0,i.RGBA,1,1,Oe,0,i.RGBA,i.UNSIGNED_BYTE,Pe):i.texImage2D(me+Je,0,i.RGBA,1,1,0,i.RGBA,i.UNSIGNED_BYTE,Pe);return Ze}const Ue={};Ue[i.TEXTURE_2D]=Te(i.TEXTURE_2D,i.TEXTURE_2D,1),Ue[i.TEXTURE_CUBE_MAP]=Te(i.TEXTURE_CUBE_MAP,i.TEXTURE_CUBE_MAP_POSITIVE_X,6),n&&(Ue[i.TEXTURE_2D_ARRAY]=Te(i.TEXTURE_2D_ARRAY,i.TEXTURE_2D_ARRAY,1,1),Ue[i.TEXTURE_3D]=Te(i.TEXTURE_3D,i.TEXTURE_3D,1,1)),a.setClear(0,0,0,1),l.setClear(1),c.setClear(0),Ie(i.DEPTH_TEST),l.setFunc(Va),ae(!1),T(Ff),Ie(i.CULL_FACE),K(Zi);function Ie(F){h[F]!==!0&&(i.enable(F),h[F]=!0)}function Se(F){h[F]!==!1&&(i.disable(F),h[F]=!1)}function Ke(F,me){return d[F]!==me?(i.bindFramebuffer(F,me),d[F]=me,n&&(F===i.DRAW_FRAMEBUFFER&&(d[i.FRAMEBUFFER]=me),F===i.FRAMEBUFFER&&(d[i.DRAW_FRAMEBUFFER]=me)),!0):!1}function E(F,me){let ye=_,Oe=!1;if(F)if(ye=g.get(me),ye===void 0&&(ye=[],g.set(me,ye)),F.isWebGLMultipleRenderTargets){const Pe=F.texture;if(ye.length!==Pe.length||ye[0]!==i.COLOR_ATTACHMENT0){for(let Ze=0,Je=Pe.length;Ze<Je;Ze++)ye[Ze]=i.COLOR_ATTACHMENT0+Ze;ye.length=Pe.length,Oe=!0}}else ye[0]!==i.COLOR_ATTACHMENT0&&(ye[0]=i.COLOR_ATTACHMENT0,Oe=!0);else ye[0]!==i.BACK&&(ye[0]=i.BACK,Oe=!0);Oe&&(t.isWebGL2?i.drawBuffers(ye):e.get("WEBGL_draw_buffers").drawBuffersWEBGL(ye))}function z(F){return m!==F?(i.useProgram(F),m=F,!0):!1}const V={[Ts]:i.FUNC_ADD,[Q0]:i.FUNC_SUBTRACT,[ev]:i.FUNC_REVERSE_SUBTRACT};if(n)V[kf]=i.MIN,V[Vf]=i.MAX;else{const F=e.get("EXT_blend_minmax");F!==null&&(V[kf]=F.MIN_EXT,V[Vf]=F.MAX_EXT)}const te={[tv]:i.ZERO,[nv]:i.ONE,[iv]:i.SRC_COLOR,[Oc]:i.SRC_ALPHA,[cv]:i.SRC_ALPHA_SATURATE,[av]:i.DST_COLOR,[rv]:i.DST_ALPHA,[sv]:i.ONE_MINUS_SRC_COLOR,[Nc]:i.ONE_MINUS_SRC_ALPHA,[lv]:i.ONE_MINUS_DST_COLOR,[ov]:i.ONE_MINUS_DST_ALPHA,[uv]:i.CONSTANT_COLOR,[fv]:i.ONE_MINUS_CONSTANT_COLOR,[hv]:i.CONSTANT_ALPHA,[dv]:i.ONE_MINUS_CONSTANT_ALPHA};function K(F,me,ye,Oe,Pe,Ze,Je,St,Tt,nt){if(F===Zi){p===!0&&(Se(i.BLEND),p=!1);return}if(p===!1&&(Ie(i.BLEND),p=!0),F!==J0){if(F!==x||nt!==N){if((y!==Ts||L!==Ts)&&(i.blendEquation(i.FUNC_ADD),y=Ts,L=Ts),nt)switch(F){case Ji:i.blendFuncSeparate(i.ONE,i.ONE_MINUS_SRC_ALPHA,i.ONE,i.ONE_MINUS_SRC_ALPHA);break;case ka:i.blendFunc(i.ONE,i.ONE);break;case zf:i.blendFuncSeparate(i.ZERO,i.ONE_MINUS_SRC_COLOR,i.ZERO,i.ONE);break;case Bf:i.blendFuncSeparate(i.ZERO,i.SRC_COLOR,i.ZERO,i.SRC_ALPHA);break;default:console.error("THREE.WebGLState: Invalid blending: ",F);break}else switch(F){case Ji:i.blendFuncSeparate(i.SRC_ALPHA,i.ONE_MINUS_SRC_ALPHA,i.ONE,i.ONE_MINUS_SRC_ALPHA);break;case ka:i.blendFunc(i.SRC_ALPHA,i.ONE);break;case zf:i.blendFuncSeparate(i.ZERO,i.ONE_MINUS_SRC_COLOR,i.ZERO,i.ONE);break;case Bf:i.blendFunc(i.ZERO,i.SRC_COLOR);break;default:console.error("THREE.WebGLState: Invalid blending: ",F);break}S=null,R=null,w=null,B=null,v.set(0,0,0),b=0,x=F,N=nt}return}Pe=Pe||me,Ze=Ze||ye,Je=Je||Oe,(me!==y||Pe!==L)&&(i.blendEquationSeparate(V[me],V[Pe]),y=me,L=Pe),(ye!==S||Oe!==R||Ze!==w||Je!==B)&&(i.blendFuncSeparate(te[ye],te[Oe],te[Ze],te[Je]),S=ye,R=Oe,w=Ze,B=Je),(St.equals(v)===!1||Tt!==b)&&(i.blendColor(St.r,St.g,St.b,Tt),v.copy(St),b=Tt),x=F,N=!1}function oe(F,me){F.side===Ai?Se(i.CULL_FACE):Ie(i.CULL_FACE);let ye=F.side===un;me&&(ye=!ye),ae(ye),F.blending===Ji&&F.transparent===!1?K(Zi):K(F.blending,F.blendEquation,F.blendSrc,F.blendDst,F.blendEquationAlpha,F.blendSrcAlpha,F.blendDstAlpha,F.blendColor,F.blendAlpha,F.premultipliedAlpha),l.setFunc(F.depthFunc),l.setTest(F.depthTest),l.setMask(F.depthWrite),a.setMask(F.colorWrite);const Oe=F.stencilWrite;c.setTest(Oe),Oe&&(c.setMask(F.stencilWriteMask),c.setFunc(F.stencilFunc,F.stencilRef,F.stencilFuncMask),c.setOp(F.stencilFail,F.stencilZFail,F.stencilZPass)),U(F.polygonOffset,F.polygonOffsetFactor,F.polygonOffsetUnits),F.alphaToCoverage===!0?Ie(i.SAMPLE_ALPHA_TO_COVERAGE):Se(i.SAMPLE_ALPHA_TO_COVERAGE)}function ae(F){A!==F&&(F?i.frontFace(i.CW):i.frontFace(i.CCW),A=F)}function T(F){F!==j0?(Ie(i.CULL_FACE),F!==I&&(F===Ff?i.cullFace(i.BACK):F===K0?i.cullFace(i.FRONT):i.cullFace(i.FRONT_AND_BACK))):Se(i.CULL_FACE),I=F}function M(F){F!==O&&(Z&&i.lineWidth(F),O=F)}function U(F,me,ye){F?(Ie(i.POLYGON_OFFSET_FILL),(k!==me||H!==ye)&&(i.polygonOffset(me,ye),k=me,H=ye)):Se(i.POLYGON_OFFSET_FILL)}function ee(F){F?Ie(i.SCISSOR_TEST):Se(i.SCISSOR_TEST)}function X(F){F===void 0&&(F=i.TEXTURE0+q-1),G!==F&&(i.activeTexture(F),G=F)}function J(F,me,ye){ye===void 0&&(G===null?ye=i.TEXTURE0+q-1:ye=G);let Oe=re[ye];Oe===void 0&&(Oe={type:void 0,texture:void 0},re[ye]=Oe),(Oe.type!==F||Oe.texture!==me)&&(G!==ye&&(i.activeTexture(ye),G=ye),i.bindTexture(F,me||Ue[F]),Oe.type=F,Oe.texture=me)}function fe(){const F=re[G];F!==void 0&&F.type!==void 0&&(i.bindTexture(F.type,null),F.type=void 0,F.texture=void 0)}function ue(){try{i.compressedTexImage2D.apply(i,arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function de(){try{i.compressedTexImage3D.apply(i,arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function xe(){try{i.texSubImage2D.apply(i,arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function Ae(){try{i.texSubImage3D.apply(i,arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function ce(){try{i.compressedTexSubImage2D.apply(i,arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function ke(){try{i.compressedTexSubImage3D.apply(i,arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function De(){try{i.texStorage2D.apply(i,arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function Le(){try{i.texStorage3D.apply(i,arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function Re(){try{i.texImage2D.apply(i,arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function ge(){try{i.texImage3D.apply(i,arguments)}catch(F){console.error("THREE.WebGLState:",F)}}function D(F){_e.equals(F)===!1&&(i.scissor(F.x,F.y,F.z,F.w),_e.copy(F))}function pe(F){be.equals(F)===!1&&(i.viewport(F.x,F.y,F.z,F.w),be.copy(F))}function we(F,me){let ye=f.get(me);ye===void 0&&(ye=new WeakMap,f.set(me,ye));let Oe=ye.get(F);Oe===void 0&&(Oe=i.getUniformBlockIndex(me,F.name),ye.set(F,Oe))}function Ee(F,me){const Oe=f.get(me).get(F);u.get(me)!==Oe&&(i.uniformBlockBinding(me,Oe,F.__bindingPointIndex),u.set(me,Oe))}function he(){i.disable(i.BLEND),i.disable(i.CULL_FACE),i.disable(i.DEPTH_TEST),i.disable(i.POLYGON_OFFSET_FILL),i.disable(i.SCISSOR_TEST),i.disable(i.STENCIL_TEST),i.disable(i.SAMPLE_ALPHA_TO_COVERAGE),i.blendEquation(i.FUNC_ADD),i.blendFunc(i.ONE,i.ZERO),i.blendFuncSeparate(i.ONE,i.ZERO,i.ONE,i.ZERO),i.blendColor(0,0,0,0),i.colorMask(!0,!0,!0,!0),i.clearColor(0,0,0,0),i.depthMask(!0),i.depthFunc(i.LESS),i.clearDepth(1),i.stencilMask(4294967295),i.stencilFunc(i.ALWAYS,0,4294967295),i.stencilOp(i.KEEP,i.KEEP,i.KEEP),i.clearStencil(0),i.cullFace(i.BACK),i.frontFace(i.CCW),i.polygonOffset(0,0),i.activeTexture(i.TEXTURE0),i.bindFramebuffer(i.FRAMEBUFFER,null),n===!0&&(i.bindFramebuffer(i.DRAW_FRAMEBUFFER,null),i.bindFramebuffer(i.READ_FRAMEBUFFER,null)),i.useProgram(null),i.lineWidth(1),i.scissor(0,0,i.canvas.width,i.canvas.height),i.viewport(0,0,i.canvas.width,i.canvas.height),h={},G=null,re={},d={},g=new WeakMap,_=[],m=null,p=!1,x=null,y=null,S=null,R=null,L=null,w=null,B=null,v=new Qe(0,0,0),b=0,N=!1,A=null,I=null,O=null,k=null,H=null,_e.set(0,0,i.canvas.width,i.canvas.height),be.set(0,0,i.canvas.width,i.canvas.height),a.reset(),l.reset(),c.reset()}return{buffers:{color:a,depth:l,stencil:c},enable:Ie,disable:Se,bindFramebuffer:Ke,drawBuffers:E,useProgram:z,setBlending:K,setMaterial:oe,setFlipSided:ae,setCullFace:T,setLineWidth:M,setPolygonOffset:U,setScissorTest:ee,activeTexture:X,bindTexture:J,unbindTexture:fe,compressedTexImage2D:ue,compressedTexImage3D:de,texImage2D:Re,texImage3D:ge,updateUBOMapping:we,uniformBlockBinding:Ee,texStorage2D:De,texStorage3D:Le,texSubImage2D:xe,texSubImage3D:Ae,compressedTexSubImage2D:ce,compressedTexSubImage3D:ke,scissor:D,viewport:pe,reset:he}}function jE(i,e,t,n,s,r,o){const a=s.isWebGL2,l=e.has("WEBGL_multisampled_render_to_texture")?e.get("WEBGL_multisampled_render_to_texture"):null,c=typeof navigator>"u"?!1:/OculusBrowser/g.test(navigator.userAgent),u=new WeakMap;let f;const h=new WeakMap;let d=!1;try{d=typeof OffscreenCanvas<"u"&&new OffscreenCanvas(1,1).getContext("2d")!==null}catch{}function g(T,M){return d?new OffscreenCanvas(T,M):qa("canvas")}function _(T,M,U,ee){let X=1;if((T.width>ee||T.height>ee)&&(X=ee/Math.max(T.width,T.height)),X<1||M===!0)if(typeof HTMLImageElement<"u"&&T instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&T instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&T instanceof ImageBitmap){const J=M?Gc:Math.floor,fe=J(X*T.width),ue=J(X*T.height);f===void 0&&(f=g(fe,ue));const de=U?g(fe,ue):f;return de.width=fe,de.height=ue,de.getContext("2d").drawImage(T,0,0,fe,ue),console.warn("THREE.WebGLRenderer: Texture has been resized from ("+T.width+"x"+T.height+") to ("+fe+"x"+ue+")."),de}else return"data"in T&&console.warn("THREE.WebGLRenderer: Image in DataTexture is too big ("+T.width+"x"+T.height+")."),T;return T}function m(T){return gh(T.width)&&gh(T.height)}function p(T){return a?!1:T.wrapS!==Wn||T.wrapT!==Wn||T.minFilter!==tn&&T.minFilter!==Dn}function x(T,M){return T.generateMipmaps&&M&&T.minFilter!==tn&&T.minFilter!==Dn}function y(T){i.generateMipmap(T)}function S(T,M,U,ee,X=!1){if(a===!1)return M;if(T!==null){if(i[T]!==void 0)return i[T];console.warn("THREE.WebGLRenderer: Attempt to use non-existing WebGL internal format '"+T+"'")}let J=M;if(M===i.RED&&(U===i.FLOAT&&(J=i.R32F),U===i.HALF_FLOAT&&(J=i.R16F),U===i.UNSIGNED_BYTE&&(J=i.R8)),M===i.RED_INTEGER&&(U===i.UNSIGNED_BYTE&&(J=i.R8UI),U===i.UNSIGNED_SHORT&&(J=i.R16UI),U===i.UNSIGNED_INT&&(J=i.R32UI),U===i.BYTE&&(J=i.R8I),U===i.SHORT&&(J=i.R16I),U===i.INT&&(J=i.R32I)),M===i.RG&&(U===i.FLOAT&&(J=i.RG32F),U===i.HALF_FLOAT&&(J=i.RG16F),U===i.UNSIGNED_BYTE&&(J=i.RG8)),M===i.RGBA){const fe=X?Ha:at.getTransfer(ee);U===i.FLOAT&&(J=i.RGBA32F),U===i.HALF_FLOAT&&(J=i.RGBA16F),U===i.UNSIGNED_BYTE&&(J=fe===mt?i.SRGB8_ALPHA8:i.RGBA8),U===i.UNSIGNED_SHORT_4_4_4_4&&(J=i.RGBA4),U===i.UNSIGNED_SHORT_5_5_5_1&&(J=i.RGB5_A1)}return(J===i.R16F||J===i.R32F||J===i.RG16F||J===i.RG32F||J===i.RGBA16F||J===i.RGBA32F)&&e.get("EXT_color_buffer_float"),J}function R(T,M,U){return x(T,U)===!0||T.isFramebufferTexture&&T.minFilter!==tn&&T.minFilter!==Dn?Math.log2(Math.max(M.width,M.height))+1:T.mipmaps!==void 0&&T.mipmaps.length>0?T.mipmaps.length:T.isCompressedTexture&&Array.isArray(T.image)?M.mipmaps.length:1}function L(T){return T===tn||T===Hf||T===Fl?i.NEAREST:i.LINEAR}function w(T){const M=T.target;M.removeEventListener("dispose",w),v(M),M.isVideoTexture&&u.delete(M)}function B(T){const M=T.target;M.removeEventListener("dispose",B),N(M)}function v(T){const M=n.get(T);if(M.__webglInit===void 0)return;const U=T.source,ee=h.get(U);if(ee){const X=ee[M.__cacheKey];X.usedTimes--,X.usedTimes===0&&b(T),Object.keys(ee).length===0&&h.delete(U)}n.remove(T)}function b(T){const M=n.get(T);i.deleteTexture(M.__webglTexture);const U=T.source,ee=h.get(U);delete ee[M.__cacheKey],o.memory.textures--}function N(T){const M=T.texture,U=n.get(T),ee=n.get(M);if(ee.__webglTexture!==void 0&&(i.deleteTexture(ee.__webglTexture),o.memory.textures--),T.depthTexture&&T.depthTexture.dispose(),T.isWebGLCubeRenderTarget)for(let X=0;X<6;X++){if(Array.isArray(U.__webglFramebuffer[X]))for(let J=0;J<U.__webglFramebuffer[X].length;J++)i.deleteFramebuffer(U.__webglFramebuffer[X][J]);else i.deleteFramebuffer(U.__webglFramebuffer[X]);U.__webglDepthbuffer&&i.deleteRenderbuffer(U.__webglDepthbuffer[X])}else{if(Array.isArray(U.__webglFramebuffer))for(let X=0;X<U.__webglFramebuffer.length;X++)i.deleteFramebuffer(U.__webglFramebuffer[X]);else i.deleteFramebuffer(U.__webglFramebuffer);if(U.__webglDepthbuffer&&i.deleteRenderbuffer(U.__webglDepthbuffer),U.__webglMultisampledFramebuffer&&i.deleteFramebuffer(U.__webglMultisampledFramebuffer),U.__webglColorRenderbuffer)for(let X=0;X<U.__webglColorRenderbuffer.length;X++)U.__webglColorRenderbuffer[X]&&i.deleteRenderbuffer(U.__webglColorRenderbuffer[X]);U.__webglDepthRenderbuffer&&i.deleteRenderbuffer(U.__webglDepthRenderbuffer)}if(T.isWebGLMultipleRenderTargets)for(let X=0,J=M.length;X<J;X++){const fe=n.get(M[X]);fe.__webglTexture&&(i.deleteTexture(fe.__webglTexture),o.memory.textures--),n.remove(M[X])}n.remove(M),n.remove(T)}let A=0;function I(){A=0}function O(){const T=A;return T>=s.maxTextures&&console.warn("THREE.WebGLTextures: Trying to use "+T+" texture units while this GPU supports only "+s.maxTextures),A+=1,T}function k(T){const M=[];return M.push(T.wrapS),M.push(T.wrapT),M.push(T.wrapR||0),M.push(T.magFilter),M.push(T.minFilter),M.push(T.anisotropy),M.push(T.internalFormat),M.push(T.format),M.push(T.type),M.push(T.generateMipmaps),M.push(T.premultiplyAlpha),M.push(T.flipY),M.push(T.unpackAlignment),M.push(T.colorSpace),M.join()}function H(T,M){const U=n.get(T);if(T.isVideoTexture&&oe(T),T.isRenderTargetTexture===!1&&T.version>0&&U.__version!==T.version){const ee=T.image;if(ee===null)console.warn("THREE.WebGLRenderer: Texture marked for update but no image data found.");else if(ee.complete===!1)console.warn("THREE.WebGLRenderer: Texture marked for update but image is incomplete");else{_e(U,T,M);return}}t.bindTexture(i.TEXTURE_2D,U.__webglTexture,i.TEXTURE0+M)}function q(T,M){const U=n.get(T);if(T.version>0&&U.__version!==T.version){_e(U,T,M);return}t.bindTexture(i.TEXTURE_2D_ARRAY,U.__webglTexture,i.TEXTURE0+M)}function Z(T,M){const U=n.get(T);if(T.version>0&&U.__version!==T.version){_e(U,T,M);return}t.bindTexture(i.TEXTURE_3D,U.__webglTexture,i.TEXTURE0+M)}function W(T,M){const U=n.get(T);if(T.version>0&&U.__version!==T.version){be(U,T,M);return}t.bindTexture(i.TEXTURE_CUBE_MAP,U.__webglTexture,i.TEXTURE0+M)}const j={[Bc]:i.REPEAT,[Wn]:i.CLAMP_TO_EDGE,[kc]:i.MIRRORED_REPEAT},G={[tn]:i.NEAREST,[Hf]:i.NEAREST_MIPMAP_NEAREST,[Fl]:i.NEAREST_MIPMAP_LINEAR,[Dn]:i.LINEAR,[Cv]:i.LINEAR_MIPMAP_NEAREST,[yo]:i.LINEAR_MIPMAP_LINEAR},re={[Hv]:i.NEVER,[$v]:i.ALWAYS,[Gv]:i.LESS,[Kp]:i.LEQUAL,[Wv]:i.EQUAL,[Yv]:i.GEQUAL,[Xv]:i.GREATER,[qv]:i.NOTEQUAL};function Q(T,M,U){if(U?(i.texParameteri(T,i.TEXTURE_WRAP_S,j[M.wrapS]),i.texParameteri(T,i.TEXTURE_WRAP_T,j[M.wrapT]),(T===i.TEXTURE_3D||T===i.TEXTURE_2D_ARRAY)&&i.texParameteri(T,i.TEXTURE_WRAP_R,j[M.wrapR]),i.texParameteri(T,i.TEXTURE_MAG_FILTER,G[M.magFilter]),i.texParameteri(T,i.TEXTURE_MIN_FILTER,G[M.minFilter])):(i.texParameteri(T,i.TEXTURE_WRAP_S,i.CLAMP_TO_EDGE),i.texParameteri(T,i.TEXTURE_WRAP_T,i.CLAMP_TO_EDGE),(T===i.TEXTURE_3D||T===i.TEXTURE_2D_ARRAY)&&i.texParameteri(T,i.TEXTURE_WRAP_R,i.CLAMP_TO_EDGE),(M.wrapS!==Wn||M.wrapT!==Wn)&&console.warn("THREE.WebGLRenderer: Texture is not power of two. Texture.wrapS and Texture.wrapT should be set to THREE.ClampToEdgeWrapping."),i.texParameteri(T,i.TEXTURE_MAG_FILTER,L(M.magFilter)),i.texParameteri(T,i.TEXTURE_MIN_FILTER,L(M.minFilter)),M.minFilter!==tn&&M.minFilter!==Dn&&console.warn("THREE.WebGLRenderer: Texture is not power of two. Texture.minFilter should be set to THREE.NearestFilter or THREE.LinearFilter.")),M.compareFunction&&(i.texParameteri(T,i.TEXTURE_COMPARE_MODE,i.COMPARE_REF_TO_TEXTURE),i.texParameteri(T,i.TEXTURE_COMPARE_FUNC,re[M.compareFunction])),e.has("EXT_texture_filter_anisotropic")===!0){const ee=e.get("EXT_texture_filter_anisotropic");if(M.magFilter===tn||M.minFilter!==Fl&&M.minFilter!==yo||M.type===qi&&e.has("OES_texture_float_linear")===!1||a===!1&&M.type===So&&e.has("OES_texture_half_float_linear")===!1)return;(M.anisotropy>1||n.get(M).__currentAnisotropy)&&(i.texParameterf(T,ee.TEXTURE_MAX_ANISOTROPY_EXT,Math.min(M.anisotropy,s.getMaxAnisotropy())),n.get(M).__currentAnisotropy=M.anisotropy)}}function le(T,M){let U=!1;T.__webglInit===void 0&&(T.__webglInit=!0,M.addEventListener("dispose",w));const ee=M.source;let X=h.get(ee);X===void 0&&(X={},h.set(ee,X));const J=k(M);if(J!==T.__cacheKey){X[J]===void 0&&(X[J]={texture:i.createTexture(),usedTimes:0},o.memory.textures++,U=!0),X[J].usedTimes++;const fe=X[T.__cacheKey];fe!==void 0&&(X[T.__cacheKey].usedTimes--,fe.usedTimes===0&&b(M)),T.__cacheKey=J,T.__webglTexture=X[J].texture}return U}function _e(T,M,U){let ee=i.TEXTURE_2D;(M.isDataArrayTexture||M.isCompressedArrayTexture)&&(ee=i.TEXTURE_2D_ARRAY),M.isData3DTexture&&(ee=i.TEXTURE_3D);const X=le(T,M),J=M.source;t.bindTexture(ee,T.__webglTexture,i.TEXTURE0+U);const fe=n.get(J);if(J.version!==fe.__version||X===!0){t.activeTexture(i.TEXTURE0+U);const ue=at.getPrimaries(at.workingColorSpace),de=M.colorSpace===In?null:at.getPrimaries(M.colorSpace),xe=M.colorSpace===In||ue===de?i.NONE:i.BROWSER_DEFAULT_WEBGL;i.pixelStorei(i.UNPACK_FLIP_Y_WEBGL,M.flipY),i.pixelStorei(i.UNPACK_PREMULTIPLY_ALPHA_WEBGL,M.premultiplyAlpha),i.pixelStorei(i.UNPACK_ALIGNMENT,M.unpackAlignment),i.pixelStorei(i.UNPACK_COLORSPACE_CONVERSION_WEBGL,xe);const Ae=p(M)&&m(M.image)===!1;let ce=_(M.image,Ae,!1,s.maxTextureSize);ce=ae(M,ce);const ke=m(ce)||a,De=r.convert(M.format,M.colorSpace);let Le=r.convert(M.type),Re=S(M.internalFormat,De,Le,M.colorSpace,M.isVideoTexture);Q(ee,M,ke);let ge;const D=M.mipmaps,pe=a&&M.isVideoTexture!==!0&&Re!==$p,we=fe.__version===void 0||X===!0,Ee=R(M,ce,ke);if(M.isDepthTexture)Re=i.DEPTH_COMPONENT,a?M.type===qi?Re=i.DEPTH_COMPONENT32F:M.type===Xi?Re=i.DEPTH_COMPONENT24:M.type===Ls?Re=i.DEPTH24_STENCIL8:Re=i.DEPTH_COMPONENT16:M.type===qi&&console.error("WebGLRenderer: Floating point depth texture requires WebGL2."),M.format===Ds&&Re===i.DEPTH_COMPONENT&&M.type!==Tu&&M.type!==Xi&&(console.warn("THREE.WebGLRenderer: Use UnsignedShortType or UnsignedIntType for DepthFormat DepthTexture."),M.type=Xi,Le=r.convert(M.type)),M.format===Pr&&Re===i.DEPTH_COMPONENT&&(Re=i.DEPTH_STENCIL,M.type!==Ls&&(console.warn("THREE.WebGLRenderer: Use UnsignedInt248Type for DepthStencilFormat DepthTexture."),M.type=Ls,Le=r.convert(M.type))),we&&(pe?t.texStorage2D(i.TEXTURE_2D,1,Re,ce.width,ce.height):t.texImage2D(i.TEXTURE_2D,0,Re,ce.width,ce.height,0,De,Le,null));else if(M.isDataTexture)if(D.length>0&&ke){pe&&we&&t.texStorage2D(i.TEXTURE_2D,Ee,Re,D[0].width,D[0].height);for(let he=0,F=D.length;he<F;he++)ge=D[he],pe?t.texSubImage2D(i.TEXTURE_2D,he,0,0,ge.width,ge.height,De,Le,ge.data):t.texImage2D(i.TEXTURE_2D,he,Re,ge.width,ge.height,0,De,Le,ge.data);M.generateMipmaps=!1}else pe?(we&&t.texStorage2D(i.TEXTURE_2D,Ee,Re,ce.width,ce.height),t.texSubImage2D(i.TEXTURE_2D,0,0,0,ce.width,ce.height,De,Le,ce.data)):t.texImage2D(i.TEXTURE_2D,0,Re,ce.width,ce.height,0,De,Le,ce.data);else if(M.isCompressedTexture)if(M.isCompressedArrayTexture){pe&&we&&t.texStorage3D(i.TEXTURE_2D_ARRAY,Ee,Re,D[0].width,D[0].height,ce.depth);for(let he=0,F=D.length;he<F;he++)ge=D[he],M.format!==Xn?De!==null?pe?t.compressedTexSubImage3D(i.TEXTURE_2D_ARRAY,he,0,0,0,ge.width,ge.height,ce.depth,De,ge.data,0,0):t.compressedTexImage3D(i.TEXTURE_2D_ARRAY,he,Re,ge.width,ge.height,ce.depth,0,ge.data,0,0):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()"):pe?t.texSubImage3D(i.TEXTURE_2D_ARRAY,he,0,0,0,ge.width,ge.height,ce.depth,De,Le,ge.data):t.texImage3D(i.TEXTURE_2D_ARRAY,he,Re,ge.width,ge.height,ce.depth,0,De,Le,ge.data)}else{pe&&we&&t.texStorage2D(i.TEXTURE_2D,Ee,Re,D[0].width,D[0].height);for(let he=0,F=D.length;he<F;he++)ge=D[he],M.format!==Xn?De!==null?pe?t.compressedTexSubImage2D(i.TEXTURE_2D,he,0,0,ge.width,ge.height,De,ge.data):t.compressedTexImage2D(i.TEXTURE_2D,he,Re,ge.width,ge.height,0,ge.data):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()"):pe?t.texSubImage2D(i.TEXTURE_2D,he,0,0,ge.width,ge.height,De,Le,ge.data):t.texImage2D(i.TEXTURE_2D,he,Re,ge.width,ge.height,0,De,Le,ge.data)}else if(M.isDataArrayTexture)pe?(we&&t.texStorage3D(i.TEXTURE_2D_ARRAY,Ee,Re,ce.width,ce.height,ce.depth),t.texSubImage3D(i.TEXTURE_2D_ARRAY,0,0,0,0,ce.width,ce.height,ce.depth,De,Le,ce.data)):t.texImage3D(i.TEXTURE_2D_ARRAY,0,Re,ce.width,ce.height,ce.depth,0,De,Le,ce.data);else if(M.isData3DTexture)pe?(we&&t.texStorage3D(i.TEXTURE_3D,Ee,Re,ce.width,ce.height,ce.depth),t.texSubImage3D(i.TEXTURE_3D,0,0,0,0,ce.width,ce.height,ce.depth,De,Le,ce.data)):t.texImage3D(i.TEXTURE_3D,0,Re,ce.width,ce.height,ce.depth,0,De,Le,ce.data);else if(M.isFramebufferTexture){if(we)if(pe)t.texStorage2D(i.TEXTURE_2D,Ee,Re,ce.width,ce.height);else{let he=ce.width,F=ce.height;for(let me=0;me<Ee;me++)t.texImage2D(i.TEXTURE_2D,me,Re,he,F,0,De,Le,null),he>>=1,F>>=1}}else if(D.length>0&&ke){pe&&we&&t.texStorage2D(i.TEXTURE_2D,Ee,Re,D[0].width,D[0].height);for(let he=0,F=D.length;he<F;he++)ge=D[he],pe?t.texSubImage2D(i.TEXTURE_2D,he,0,0,De,Le,ge):t.texImage2D(i.TEXTURE_2D,he,Re,De,Le,ge);M.generateMipmaps=!1}else pe?(we&&t.texStorage2D(i.TEXTURE_2D,Ee,Re,ce.width,ce.height),t.texSubImage2D(i.TEXTURE_2D,0,0,0,De,Le,ce)):t.texImage2D(i.TEXTURE_2D,0,Re,De,Le,ce);x(M,ke)&&y(ee),fe.__version=J.version,M.onUpdate&&M.onUpdate(M)}T.__version=M.version}function be(T,M,U){if(M.image.length!==6)return;const ee=le(T,M),X=M.source;t.bindTexture(i.TEXTURE_CUBE_MAP,T.__webglTexture,i.TEXTURE0+U);const J=n.get(X);if(X.version!==J.__version||ee===!0){t.activeTexture(i.TEXTURE0+U);const fe=at.getPrimaries(at.workingColorSpace),ue=M.colorSpace===In?null:at.getPrimaries(M.colorSpace),de=M.colorSpace===In||fe===ue?i.NONE:i.BROWSER_DEFAULT_WEBGL;i.pixelStorei(i.UNPACK_FLIP_Y_WEBGL,M.flipY),i.pixelStorei(i.UNPACK_PREMULTIPLY_ALPHA_WEBGL,M.premultiplyAlpha),i.pixelStorei(i.UNPACK_ALIGNMENT,M.unpackAlignment),i.pixelStorei(i.UNPACK_COLORSPACE_CONVERSION_WEBGL,de);const xe=M.isCompressedTexture||M.image[0].isCompressedTexture,Ae=M.image[0]&&M.image[0].isDataTexture,ce=[];for(let he=0;he<6;he++)!xe&&!Ae?ce[he]=_(M.image[he],!1,!0,s.maxCubemapSize):ce[he]=Ae?M.image[he].image:M.image[he],ce[he]=ae(M,ce[he]);const ke=ce[0],De=m(ke)||a,Le=r.convert(M.format,M.colorSpace),Re=r.convert(M.type),ge=S(M.internalFormat,Le,Re,M.colorSpace),D=a&&M.isVideoTexture!==!0,pe=J.__version===void 0||ee===!0;let we=R(M,ke,De);Q(i.TEXTURE_CUBE_MAP,M,De);let Ee;if(xe){D&&pe&&t.texStorage2D(i.TEXTURE_CUBE_MAP,we,ge,ke.width,ke.height);for(let he=0;he<6;he++){Ee=ce[he].mipmaps;for(let F=0;F<Ee.length;F++){const me=Ee[F];M.format!==Xn?Le!==null?D?t.compressedTexSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+he,F,0,0,me.width,me.height,Le,me.data):t.compressedTexImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+he,F,ge,me.width,me.height,0,me.data):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .setTextureCube()"):D?t.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+he,F,0,0,me.width,me.height,Le,Re,me.data):t.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+he,F,ge,me.width,me.height,0,Le,Re,me.data)}}}else{Ee=M.mipmaps,D&&pe&&(Ee.length>0&&we++,t.texStorage2D(i.TEXTURE_CUBE_MAP,we,ge,ce[0].width,ce[0].height));for(let he=0;he<6;he++)if(Ae){D?t.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+he,0,0,0,ce[he].width,ce[he].height,Le,Re,ce[he].data):t.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+he,0,ge,ce[he].width,ce[he].height,0,Le,Re,ce[he].data);for(let F=0;F<Ee.length;F++){const ye=Ee[F].image[he].image;D?t.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+he,F+1,0,0,ye.width,ye.height,Le,Re,ye.data):t.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+he,F+1,ge,ye.width,ye.height,0,Le,Re,ye.data)}}else{D?t.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+he,0,0,0,Le,Re,ce[he]):t.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+he,0,ge,Le,Re,ce[he]);for(let F=0;F<Ee.length;F++){const me=Ee[F];D?t.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+he,F+1,0,0,Le,Re,me.image[he]):t.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+he,F+1,ge,Le,Re,me.image[he])}}}x(M,De)&&y(i.TEXTURE_CUBE_MAP),J.__version=X.version,M.onUpdate&&M.onUpdate(M)}T.__version=M.version}function Te(T,M,U,ee,X,J){const fe=r.convert(U.format,U.colorSpace),ue=r.convert(U.type),de=S(U.internalFormat,fe,ue,U.colorSpace);if(!n.get(M).__hasExternalTextures){const Ae=Math.max(1,M.width>>J),ce=Math.max(1,M.height>>J);X===i.TEXTURE_3D||X===i.TEXTURE_2D_ARRAY?t.texImage3D(X,J,de,Ae,ce,M.depth,0,fe,ue,null):t.texImage2D(X,J,de,Ae,ce,0,fe,ue,null)}t.bindFramebuffer(i.FRAMEBUFFER,T),K(M)?l.framebufferTexture2DMultisampleEXT(i.FRAMEBUFFER,ee,X,n.get(U).__webglTexture,0,te(M)):(X===i.TEXTURE_2D||X>=i.TEXTURE_CUBE_MAP_POSITIVE_X&&X<=i.TEXTURE_CUBE_MAP_NEGATIVE_Z)&&i.framebufferTexture2D(i.FRAMEBUFFER,ee,X,n.get(U).__webglTexture,J),t.bindFramebuffer(i.FRAMEBUFFER,null)}function Ue(T,M,U){if(i.bindRenderbuffer(i.RENDERBUFFER,T),M.depthBuffer&&!M.stencilBuffer){let ee=a===!0?i.DEPTH_COMPONENT24:i.DEPTH_COMPONENT16;if(U||K(M)){const X=M.depthTexture;X&&X.isDepthTexture&&(X.type===qi?ee=i.DEPTH_COMPONENT32F:X.type===Xi&&(ee=i.DEPTH_COMPONENT24));const J=te(M);K(M)?l.renderbufferStorageMultisampleEXT(i.RENDERBUFFER,J,ee,M.width,M.height):i.renderbufferStorageMultisample(i.RENDERBUFFER,J,ee,M.width,M.height)}else i.renderbufferStorage(i.RENDERBUFFER,ee,M.width,M.height);i.framebufferRenderbuffer(i.FRAMEBUFFER,i.DEPTH_ATTACHMENT,i.RENDERBUFFER,T)}else if(M.depthBuffer&&M.stencilBuffer){const ee=te(M);U&&K(M)===!1?i.renderbufferStorageMultisample(i.RENDERBUFFER,ee,i.DEPTH24_STENCIL8,M.width,M.height):K(M)?l.renderbufferStorageMultisampleEXT(i.RENDERBUFFER,ee,i.DEPTH24_STENCIL8,M.width,M.height):i.renderbufferStorage(i.RENDERBUFFER,i.DEPTH_STENCIL,M.width,M.height),i.framebufferRenderbuffer(i.FRAMEBUFFER,i.DEPTH_STENCIL_ATTACHMENT,i.RENDERBUFFER,T)}else{const ee=M.isWebGLMultipleRenderTargets===!0?M.texture:[M.texture];for(let X=0;X<ee.length;X++){const J=ee[X],fe=r.convert(J.format,J.colorSpace),ue=r.convert(J.type),de=S(J.internalFormat,fe,ue,J.colorSpace),xe=te(M);U&&K(M)===!1?i.renderbufferStorageMultisample(i.RENDERBUFFER,xe,de,M.width,M.height):K(M)?l.renderbufferStorageMultisampleEXT(i.RENDERBUFFER,xe,de,M.width,M.height):i.renderbufferStorage(i.RENDERBUFFER,de,M.width,M.height)}}i.bindRenderbuffer(i.RENDERBUFFER,null)}function Ie(T,M){if(M&&M.isWebGLCubeRenderTarget)throw new Error("Depth Texture with cube render targets is not supported");if(t.bindFramebuffer(i.FRAMEBUFFER,T),!(M.depthTexture&&M.depthTexture.isDepthTexture))throw new Error("renderTarget.depthTexture must be an instance of THREE.DepthTexture");(!n.get(M.depthTexture).__webglTexture||M.depthTexture.image.width!==M.width||M.depthTexture.image.height!==M.height)&&(M.depthTexture.image.width=M.width,M.depthTexture.image.height=M.height,M.depthTexture.needsUpdate=!0),H(M.depthTexture,0);const ee=n.get(M.depthTexture).__webglTexture,X=te(M);if(M.depthTexture.format===Ds)K(M)?l.framebufferTexture2DMultisampleEXT(i.FRAMEBUFFER,i.DEPTH_ATTACHMENT,i.TEXTURE_2D,ee,0,X):i.framebufferTexture2D(i.FRAMEBUFFER,i.DEPTH_ATTACHMENT,i.TEXTURE_2D,ee,0);else if(M.depthTexture.format===Pr)K(M)?l.framebufferTexture2DMultisampleEXT(i.FRAMEBUFFER,i.DEPTH_STENCIL_ATTACHMENT,i.TEXTURE_2D,ee,0,X):i.framebufferTexture2D(i.FRAMEBUFFER,i.DEPTH_STENCIL_ATTACHMENT,i.TEXTURE_2D,ee,0);else throw new Error("Unknown depthTexture format")}function Se(T){const M=n.get(T),U=T.isWebGLCubeRenderTarget===!0;if(T.depthTexture&&!M.__autoAllocateDepthBuffer){if(U)throw new Error("target.depthTexture not supported in Cube render targets");Ie(M.__webglFramebuffer,T)}else if(U){M.__webglDepthbuffer=[];for(let ee=0;ee<6;ee++)t.bindFramebuffer(i.FRAMEBUFFER,M.__webglFramebuffer[ee]),M.__webglDepthbuffer[ee]=i.createRenderbuffer(),Ue(M.__webglDepthbuffer[ee],T,!1)}else t.bindFramebuffer(i.FRAMEBUFFER,M.__webglFramebuffer),M.__webglDepthbuffer=i.createRenderbuffer(),Ue(M.__webglDepthbuffer,T,!1);t.bindFramebuffer(i.FRAMEBUFFER,null)}function Ke(T,M,U){const ee=n.get(T);M!==void 0&&Te(ee.__webglFramebuffer,T,T.texture,i.COLOR_ATTACHMENT0,i.TEXTURE_2D,0),U!==void 0&&Se(T)}function E(T){const M=T.texture,U=n.get(T),ee=n.get(M);T.addEventListener("dispose",B),T.isWebGLMultipleRenderTargets!==!0&&(ee.__webglTexture===void 0&&(ee.__webglTexture=i.createTexture()),ee.__version=M.version,o.memory.textures++);const X=T.isWebGLCubeRenderTarget===!0,J=T.isWebGLMultipleRenderTargets===!0,fe=m(T)||a;if(X){U.__webglFramebuffer=[];for(let ue=0;ue<6;ue++)if(a&&M.mipmaps&&M.mipmaps.length>0){U.__webglFramebuffer[ue]=[];for(let de=0;de<M.mipmaps.length;de++)U.__webglFramebuffer[ue][de]=i.createFramebuffer()}else U.__webglFramebuffer[ue]=i.createFramebuffer()}else{if(a&&M.mipmaps&&M.mipmaps.length>0){U.__webglFramebuffer=[];for(let ue=0;ue<M.mipmaps.length;ue++)U.__webglFramebuffer[ue]=i.createFramebuffer()}else U.__webglFramebuffer=i.createFramebuffer();if(J)if(s.drawBuffers){const ue=T.texture;for(let de=0,xe=ue.length;de<xe;de++){const Ae=n.get(ue[de]);Ae.__webglTexture===void 0&&(Ae.__webglTexture=i.createTexture(),o.memory.textures++)}}else console.warn("THREE.WebGLRenderer: WebGLMultipleRenderTargets can only be used with WebGL2 or WEBGL_draw_buffers extension.");if(a&&T.samples>0&&K(T)===!1){const ue=J?M:[M];U.__webglMultisampledFramebuffer=i.createFramebuffer(),U.__webglColorRenderbuffer=[],t.bindFramebuffer(i.FRAMEBUFFER,U.__webglMultisampledFramebuffer);for(let de=0;de<ue.length;de++){const xe=ue[de];U.__webglColorRenderbuffer[de]=i.createRenderbuffer(),i.bindRenderbuffer(i.RENDERBUFFER,U.__webglColorRenderbuffer[de]);const Ae=r.convert(xe.format,xe.colorSpace),ce=r.convert(xe.type),ke=S(xe.internalFormat,Ae,ce,xe.colorSpace,T.isXRRenderTarget===!0),De=te(T);i.renderbufferStorageMultisample(i.RENDERBUFFER,De,ke,T.width,T.height),i.framebufferRenderbuffer(i.FRAMEBUFFER,i.COLOR_ATTACHMENT0+de,i.RENDERBUFFER,U.__webglColorRenderbuffer[de])}i.bindRenderbuffer(i.RENDERBUFFER,null),T.depthBuffer&&(U.__webglDepthRenderbuffer=i.createRenderbuffer(),Ue(U.__webglDepthRenderbuffer,T,!0)),t.bindFramebuffer(i.FRAMEBUFFER,null)}}if(X){t.bindTexture(i.TEXTURE_CUBE_MAP,ee.__webglTexture),Q(i.TEXTURE_CUBE_MAP,M,fe);for(let ue=0;ue<6;ue++)if(a&&M.mipmaps&&M.mipmaps.length>0)for(let de=0;de<M.mipmaps.length;de++)Te(U.__webglFramebuffer[ue][de],T,M,i.COLOR_ATTACHMENT0,i.TEXTURE_CUBE_MAP_POSITIVE_X+ue,de);else Te(U.__webglFramebuffer[ue],T,M,i.COLOR_ATTACHMENT0,i.TEXTURE_CUBE_MAP_POSITIVE_X+ue,0);x(M,fe)&&y(i.TEXTURE_CUBE_MAP),t.unbindTexture()}else if(J){const ue=T.texture;for(let de=0,xe=ue.length;de<xe;de++){const Ae=ue[de],ce=n.get(Ae);t.bindTexture(i.TEXTURE_2D,ce.__webglTexture),Q(i.TEXTURE_2D,Ae,fe),Te(U.__webglFramebuffer,T,Ae,i.COLOR_ATTACHMENT0+de,i.TEXTURE_2D,0),x(Ae,fe)&&y(i.TEXTURE_2D)}t.unbindTexture()}else{let ue=i.TEXTURE_2D;if((T.isWebGL3DRenderTarget||T.isWebGLArrayRenderTarget)&&(a?ue=T.isWebGL3DRenderTarget?i.TEXTURE_3D:i.TEXTURE_2D_ARRAY:console.error("THREE.WebGLTextures: THREE.Data3DTexture and THREE.DataArrayTexture only supported with WebGL2.")),t.bindTexture(ue,ee.__webglTexture),Q(ue,M,fe),a&&M.mipmaps&&M.mipmaps.length>0)for(let de=0;de<M.mipmaps.length;de++)Te(U.__webglFramebuffer[de],T,M,i.COLOR_ATTACHMENT0,ue,de);else Te(U.__webglFramebuffer,T,M,i.COLOR_ATTACHMENT0,ue,0);x(M,fe)&&y(ue),t.unbindTexture()}T.depthBuffer&&Se(T)}function z(T){const M=m(T)||a,U=T.isWebGLMultipleRenderTargets===!0?T.texture:[T.texture];for(let ee=0,X=U.length;ee<X;ee++){const J=U[ee];if(x(J,M)){const fe=T.isWebGLCubeRenderTarget?i.TEXTURE_CUBE_MAP:i.TEXTURE_2D,ue=n.get(J).__webglTexture;t.bindTexture(fe,ue),y(fe),t.unbindTexture()}}}function V(T){if(a&&T.samples>0&&K(T)===!1){const M=T.isWebGLMultipleRenderTargets?T.texture:[T.texture],U=T.width,ee=T.height;let X=i.COLOR_BUFFER_BIT;const J=[],fe=T.stencilBuffer?i.DEPTH_STENCIL_ATTACHMENT:i.DEPTH_ATTACHMENT,ue=n.get(T),de=T.isWebGLMultipleRenderTargets===!0;if(de)for(let xe=0;xe<M.length;xe++)t.bindFramebuffer(i.FRAMEBUFFER,ue.__webglMultisampledFramebuffer),i.framebufferRenderbuffer(i.FRAMEBUFFER,i.COLOR_ATTACHMENT0+xe,i.RENDERBUFFER,null),t.bindFramebuffer(i.FRAMEBUFFER,ue.__webglFramebuffer),i.framebufferTexture2D(i.DRAW_FRAMEBUFFER,i.COLOR_ATTACHMENT0+xe,i.TEXTURE_2D,null,0);t.bindFramebuffer(i.READ_FRAMEBUFFER,ue.__webglMultisampledFramebuffer),t.bindFramebuffer(i.DRAW_FRAMEBUFFER,ue.__webglFramebuffer);for(let xe=0;xe<M.length;xe++){J.push(i.COLOR_ATTACHMENT0+xe),T.depthBuffer&&J.push(fe);const Ae=ue.__ignoreDepthValues!==void 0?ue.__ignoreDepthValues:!1;if(Ae===!1&&(T.depthBuffer&&(X|=i.DEPTH_BUFFER_BIT),T.stencilBuffer&&(X|=i.STENCIL_BUFFER_BIT)),de&&i.framebufferRenderbuffer(i.READ_FRAMEBUFFER,i.COLOR_ATTACHMENT0,i.RENDERBUFFER,ue.__webglColorRenderbuffer[xe]),Ae===!0&&(i.invalidateFramebuffer(i.READ_FRAMEBUFFER,[fe]),i.invalidateFramebuffer(i.DRAW_FRAMEBUFFER,[fe])),de){const ce=n.get(M[xe]).__webglTexture;i.framebufferTexture2D(i.DRAW_FRAMEBUFFER,i.COLOR_ATTACHMENT0,i.TEXTURE_2D,ce,0)}i.blitFramebuffer(0,0,U,ee,0,0,U,ee,X,i.NEAREST),c&&i.invalidateFramebuffer(i.READ_FRAMEBUFFER,J)}if(t.bindFramebuffer(i.READ_FRAMEBUFFER,null),t.bindFramebuffer(i.DRAW_FRAMEBUFFER,null),de)for(let xe=0;xe<M.length;xe++){t.bindFramebuffer(i.FRAMEBUFFER,ue.__webglMultisampledFramebuffer),i.framebufferRenderbuffer(i.FRAMEBUFFER,i.COLOR_ATTACHMENT0+xe,i.RENDERBUFFER,ue.__webglColorRenderbuffer[xe]);const Ae=n.get(M[xe]).__webglTexture;t.bindFramebuffer(i.FRAMEBUFFER,ue.__webglFramebuffer),i.framebufferTexture2D(i.DRAW_FRAMEBUFFER,i.COLOR_ATTACHMENT0+xe,i.TEXTURE_2D,Ae,0)}t.bindFramebuffer(i.DRAW_FRAMEBUFFER,ue.__webglMultisampledFramebuffer)}}function te(T){return Math.min(s.maxSamples,T.samples)}function K(T){const M=n.get(T);return a&&T.samples>0&&e.has("WEBGL_multisampled_render_to_texture")===!0&&M.__useRenderToTexture!==!1}function oe(T){const M=o.render.frame;u.get(T)!==M&&(u.set(T,M),T.update())}function ae(T,M){const U=T.colorSpace,ee=T.format,X=T.type;return T.isCompressedTexture===!0||T.isVideoTexture===!0||T.format===Vc||U!==Di&&U!==In&&(at.getTransfer(U)===mt?a===!1?e.has("EXT_sRGB")===!0&&ee===Xn?(T.format=Vc,T.minFilter=Dn,T.generateMipmaps=!1):M=Jp.sRGBToLinear(M):(ee!==Xn||X!==es)&&console.warn("THREE.WebGLTextures: sRGB encoded textures have to use RGBAFormat and UnsignedByteType."):console.error("THREE.WebGLTextures: Unsupported texture color space:",U)),M}this.allocateTextureUnit=O,this.resetTextureUnits=I,this.setTexture2D=H,this.setTexture2DArray=q,this.setTexture3D=Z,this.setTextureCube=W,this.rebindTextures=Ke,this.setupRenderTarget=E,this.updateRenderTargetMipmap=z,this.updateMultisampleRenderTarget=V,this.setupDepthRenderbuffer=Se,this.setupFrameBufferTexture=Te,this.useMultisampledRTT=K}function KE(i,e,t){const n=t.isWebGL2;function s(r,o=In){let a;const l=at.getTransfer(o);if(r===es)return i.UNSIGNED_BYTE;if(r===Gp)return i.UNSIGNED_SHORT_4_4_4_4;if(r===Wp)return i.UNSIGNED_SHORT_5_5_5_1;if(r===Pv)return i.BYTE;if(r===Lv)return i.SHORT;if(r===Tu)return i.UNSIGNED_SHORT;if(r===Hp)return i.INT;if(r===Xi)return i.UNSIGNED_INT;if(r===qi)return i.FLOAT;if(r===So)return n?i.HALF_FLOAT:(a=e.get("OES_texture_half_float"),a!==null?a.HALF_FLOAT_OES:null);if(r===Dv)return i.ALPHA;if(r===Xn)return i.RGBA;if(r===Uv)return i.LUMINANCE;if(r===Iv)return i.LUMINANCE_ALPHA;if(r===Ds)return i.DEPTH_COMPONENT;if(r===Pr)return i.DEPTH_STENCIL;if(r===Vc)return a=e.get("EXT_sRGB"),a!==null?a.SRGB_ALPHA_EXT:null;if(r===Ov)return i.RED;if(r===Xp)return i.RED_INTEGER;if(r===Nv)return i.RG;if(r===qp)return i.RG_INTEGER;if(r===Yp)return i.RGBA_INTEGER;if(r===zl||r===Bl||r===kl||r===Vl)if(l===mt)if(a=e.get("WEBGL_compressed_texture_s3tc_srgb"),a!==null){if(r===zl)return a.COMPRESSED_SRGB_S3TC_DXT1_EXT;if(r===Bl)return a.COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT;if(r===kl)return a.COMPRESSED_SRGB_ALPHA_S3TC_DXT3_EXT;if(r===Vl)return a.COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT}else return null;else if(a=e.get("WEBGL_compressed_texture_s3tc"),a!==null){if(r===zl)return a.COMPRESSED_RGB_S3TC_DXT1_EXT;if(r===Bl)return a.COMPRESSED_RGBA_S3TC_DXT1_EXT;if(r===kl)return a.COMPRESSED_RGBA_S3TC_DXT3_EXT;if(r===Vl)return a.COMPRESSED_RGBA_S3TC_DXT5_EXT}else return null;if(r===Gf||r===Wf||r===Xf||r===qf)if(a=e.get("WEBGL_compressed_texture_pvrtc"),a!==null){if(r===Gf)return a.COMPRESSED_RGB_PVRTC_4BPPV1_IMG;if(r===Wf)return a.COMPRESSED_RGB_PVRTC_2BPPV1_IMG;if(r===Xf)return a.COMPRESSED_RGBA_PVRTC_4BPPV1_IMG;if(r===qf)return a.COMPRESSED_RGBA_PVRTC_2BPPV1_IMG}else return null;if(r===$p)return a=e.get("WEBGL_compressed_texture_etc1"),a!==null?a.COMPRESSED_RGB_ETC1_WEBGL:null;if(r===Yf||r===$f)if(a=e.get("WEBGL_compressed_texture_etc"),a!==null){if(r===Yf)return l===mt?a.COMPRESSED_SRGB8_ETC2:a.COMPRESSED_RGB8_ETC2;if(r===$f)return l===mt?a.COMPRESSED_SRGB8_ALPHA8_ETC2_EAC:a.COMPRESSED_RGBA8_ETC2_EAC}else return null;if(r===jf||r===Kf||r===Zf||r===Jf||r===Qf||r===eh||r===th||r===nh||r===ih||r===sh||r===rh||r===oh||r===ah||r===lh)if(a=e.get("WEBGL_compressed_texture_astc"),a!==null){if(r===jf)return l===mt?a.COMPRESSED_SRGB8_ALPHA8_ASTC_4x4_KHR:a.COMPRESSED_RGBA_ASTC_4x4_KHR;if(r===Kf)return l===mt?a.COMPRESSED_SRGB8_ALPHA8_ASTC_5x4_KHR:a.COMPRESSED_RGBA_ASTC_5x4_KHR;if(r===Zf)return l===mt?a.COMPRESSED_SRGB8_ALPHA8_ASTC_5x5_KHR:a.COMPRESSED_RGBA_ASTC_5x5_KHR;if(r===Jf)return l===mt?a.COMPRESSED_SRGB8_ALPHA8_ASTC_6x5_KHR:a.COMPRESSED_RGBA_ASTC_6x5_KHR;if(r===Qf)return l===mt?a.COMPRESSED_SRGB8_ALPHA8_ASTC_6x6_KHR:a.COMPRESSED_RGBA_ASTC_6x6_KHR;if(r===eh)return l===mt?a.COMPRESSED_SRGB8_ALPHA8_ASTC_8x5_KHR:a.COMPRESSED_RGBA_ASTC_8x5_KHR;if(r===th)return l===mt?a.COMPRESSED_SRGB8_ALPHA8_ASTC_8x6_KHR:a.COMPRESSED_RGBA_ASTC_8x6_KHR;if(r===nh)return l===mt?a.COMPRESSED_SRGB8_ALPHA8_ASTC_8x8_KHR:a.COMPRESSED_RGBA_ASTC_8x8_KHR;if(r===ih)return l===mt?a.COMPRESSED_SRGB8_ALPHA8_ASTC_10x5_KHR:a.COMPRESSED_RGBA_ASTC_10x5_KHR;if(r===sh)return l===mt?a.COMPRESSED_SRGB8_ALPHA8_ASTC_10x6_KHR:a.COMPRESSED_RGBA_ASTC_10x6_KHR;if(r===rh)return l===mt?a.COMPRESSED_SRGB8_ALPHA8_ASTC_10x8_KHR:a.COMPRESSED_RGBA_ASTC_10x8_KHR;if(r===oh)return l===mt?a.COMPRESSED_SRGB8_ALPHA8_ASTC_10x10_KHR:a.COMPRESSED_RGBA_ASTC_10x10_KHR;if(r===ah)return l===mt?a.COMPRESSED_SRGB8_ALPHA8_ASTC_12x10_KHR:a.COMPRESSED_RGBA_ASTC_12x10_KHR;if(r===lh)return l===mt?a.COMPRESSED_SRGB8_ALPHA8_ASTC_12x12_KHR:a.COMPRESSED_RGBA_ASTC_12x12_KHR}else return null;if(r===Hl||r===ch||r===uh)if(a=e.get("EXT_texture_compression_bptc"),a!==null){if(r===Hl)return l===mt?a.COMPRESSED_SRGB_ALPHA_BPTC_UNORM_EXT:a.COMPRESSED_RGBA_BPTC_UNORM_EXT;if(r===ch)return a.COMPRESSED_RGB_BPTC_SIGNED_FLOAT_EXT;if(r===uh)return a.COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT_EXT}else return null;if(r===Fv||r===fh||r===hh||r===dh)if(a=e.get("EXT_texture_compression_rgtc"),a!==null){if(r===Hl)return a.COMPRESSED_RED_RGTC1_EXT;if(r===fh)return a.COMPRESSED_SIGNED_RED_RGTC1_EXT;if(r===hh)return a.COMPRESSED_RED_GREEN_RGTC2_EXT;if(r===dh)return a.COMPRESSED_SIGNED_RED_GREEN_RGTC2_EXT}else return null;return r===Ls?n?i.UNSIGNED_INT_24_8:(a=e.get("WEBGL_depth_texture"),a!==null?a.UNSIGNED_INT_24_8_WEBGL:null):i[r]!==void 0?i[r]:null}return{convert:s}}class ZE extends Un{constructor(e=[]){super(),this.isArrayCamera=!0,this.cameras=e}}class pa extends Vt{constructor(){super(),this.isGroup=!0,this.type="Group"}}const JE={type:"move"};class hc{constructor(){this._targetRay=null,this._grip=null,this._hand=null}getHandSpace(){return this._hand===null&&(this._hand=new pa,this._hand.matrixAutoUpdate=!1,this._hand.visible=!1,this._hand.joints={},this._hand.inputState={pinching:!1}),this._hand}getTargetRaySpace(){return this._targetRay===null&&(this._targetRay=new pa,this._targetRay.matrixAutoUpdate=!1,this._targetRay.visible=!1,this._targetRay.hasLinearVelocity=!1,this._targetRay.linearVelocity=new $,this._targetRay.hasAngularVelocity=!1,this._targetRay.angularVelocity=new $),this._targetRay}getGripSpace(){return this._grip===null&&(this._grip=new pa,this._grip.matrixAutoUpdate=!1,this._grip.visible=!1,this._grip.hasLinearVelocity=!1,this._grip.linearVelocity=new $,this._grip.hasAngularVelocity=!1,this._grip.angularVelocity=new $),this._grip}dispatchEvent(e){return this._targetRay!==null&&this._targetRay.dispatchEvent(e),this._grip!==null&&this._grip.dispatchEvent(e),this._hand!==null&&this._hand.dispatchEvent(e),this}connect(e){if(e&&e.hand){const t=this._hand;if(t)for(const n of e.hand.values())this._getHandJoint(t,n)}return this.dispatchEvent({type:"connected",data:e}),this}disconnect(e){return this.dispatchEvent({type:"disconnected",data:e}),this._targetRay!==null&&(this._targetRay.visible=!1),this._grip!==null&&(this._grip.visible=!1),this._hand!==null&&(this._hand.visible=!1),this}update(e,t,n){let s=null,r=null,o=null;const a=this._targetRay,l=this._grip,c=this._hand;if(e&&t.session.visibilityState!=="visible-blurred"){if(c&&e.hand){o=!0;for(const _ of e.hand.values()){const m=t.getJointPose(_,n),p=this._getHandJoint(c,_);m!==null&&(p.matrix.fromArray(m.transform.matrix),p.matrix.decompose(p.position,p.rotation,p.scale),p.matrixWorldNeedsUpdate=!0,p.jointRadius=m.radius),p.visible=m!==null}const u=c.joints["index-finger-tip"],f=c.joints["thumb-tip"],h=u.position.distanceTo(f.position),d=.02,g=.005;c.inputState.pinching&&h>d+g?(c.inputState.pinching=!1,this.dispatchEvent({type:"pinchend",handedness:e.handedness,target:this})):!c.inputState.pinching&&h<=d-g&&(c.inputState.pinching=!0,this.dispatchEvent({type:"pinchstart",handedness:e.handedness,target:this}))}else l!==null&&e.gripSpace&&(r=t.getPose(e.gripSpace,n),r!==null&&(l.matrix.fromArray(r.transform.matrix),l.matrix.decompose(l.position,l.rotation,l.scale),l.matrixWorldNeedsUpdate=!0,r.linearVelocity?(l.hasLinearVelocity=!0,l.linearVelocity.copy(r.linearVelocity)):l.hasLinearVelocity=!1,r.angularVelocity?(l.hasAngularVelocity=!0,l.angularVelocity.copy(r.angularVelocity)):l.hasAngularVelocity=!1));a!==null&&(s=t.getPose(e.targetRaySpace,n),s===null&&r!==null&&(s=r),s!==null&&(a.matrix.fromArray(s.transform.matrix),a.matrix.decompose(a.position,a.rotation,a.scale),a.matrixWorldNeedsUpdate=!0,s.linearVelocity?(a.hasLinearVelocity=!0,a.linearVelocity.copy(s.linearVelocity)):a.hasLinearVelocity=!1,s.angularVelocity?(a.hasAngularVelocity=!0,a.angularVelocity.copy(s.angularVelocity)):a.hasAngularVelocity=!1,this.dispatchEvent(JE)))}return a!==null&&(a.visible=s!==null),l!==null&&(l.visible=r!==null),c!==null&&(c.visible=o!==null),this}_getHandJoint(e,t){if(e.joints[t.jointName]===void 0){const n=new pa;n.matrixAutoUpdate=!1,n.visible=!1,e.joints[t.jointName]=n,e.add(n)}return e.joints[t.jointName]}}class QE extends Hs{constructor(e,t){super();const n=this;let s=null,r=1,o=null,a="local-floor",l=1,c=null,u=null,f=null,h=null,d=null,g=null;const _=t.getContextAttributes();let m=null,p=null;const x=[],y=[],S=new He;let R=null;const L=new Un;L.layers.enable(1),L.viewport=new Ft;const w=new Un;w.layers.enable(2),w.viewport=new Ft;const B=[L,w],v=new ZE;v.layers.enable(1),v.layers.enable(2);let b=null,N=null;this.cameraAutoUpdate=!0,this.enabled=!1,this.isPresenting=!1,this.getController=function(Q){let le=x[Q];return le===void 0&&(le=new hc,x[Q]=le),le.getTargetRaySpace()},this.getControllerGrip=function(Q){let le=x[Q];return le===void 0&&(le=new hc,x[Q]=le),le.getGripSpace()},this.getHand=function(Q){let le=x[Q];return le===void 0&&(le=new hc,x[Q]=le),le.getHandSpace()};function A(Q){const le=y.indexOf(Q.inputSource);if(le===-1)return;const _e=x[le];_e!==void 0&&(_e.update(Q.inputSource,Q.frame,c||o),_e.dispatchEvent({type:Q.type,data:Q.inputSource}))}function I(){s.removeEventListener("select",A),s.removeEventListener("selectstart",A),s.removeEventListener("selectend",A),s.removeEventListener("squeeze",A),s.removeEventListener("squeezestart",A),s.removeEventListener("squeezeend",A),s.removeEventListener("end",I),s.removeEventListener("inputsourceschange",O);for(let Q=0;Q<x.length;Q++){const le=y[Q];le!==null&&(y[Q]=null,x[Q].disconnect(le))}b=null,N=null,e.setRenderTarget(m),d=null,h=null,f=null,s=null,p=null,re.stop(),n.isPresenting=!1,e.setPixelRatio(R),e.setSize(S.width,S.height,!1),n.dispatchEvent({type:"sessionend"})}this.setFramebufferScaleFactor=function(Q){r=Q,n.isPresenting===!0&&console.warn("THREE.WebXRManager: Cannot change framebuffer scale while presenting.")},this.setReferenceSpaceType=function(Q){a=Q,n.isPresenting===!0&&console.warn("THREE.WebXRManager: Cannot change reference space type while presenting.")},this.getReferenceSpace=function(){return c||o},this.setReferenceSpace=function(Q){c=Q},this.getBaseLayer=function(){return h!==null?h:d},this.getBinding=function(){return f},this.getFrame=function(){return g},this.getSession=function(){return s},this.setSession=async function(Q){if(s=Q,s!==null){if(m=e.getRenderTarget(),s.addEventListener("select",A),s.addEventListener("selectstart",A),s.addEventListener("selectend",A),s.addEventListener("squeeze",A),s.addEventListener("squeezestart",A),s.addEventListener("squeezeend",A),s.addEventListener("end",I),s.addEventListener("inputsourceschange",O),_.xrCompatible!==!0&&await t.makeXRCompatible(),R=e.getPixelRatio(),e.getSize(S),s.renderState.layers===void 0||e.capabilities.isWebGL2===!1){const le={antialias:s.renderState.layers===void 0?_.antialias:!0,alpha:!0,depth:_.depth,stencil:_.stencil,framebufferScaleFactor:r};d=new XRWebGLLayer(s,t,le),s.updateRenderState({baseLayer:d}),e.setPixelRatio(1),e.setSize(d.framebufferWidth,d.framebufferHeight,!1),p=new Bs(d.framebufferWidth,d.framebufferHeight,{format:Xn,type:es,colorSpace:e.outputColorSpace,stencilBuffer:_.stencil})}else{let le=null,_e=null,be=null;_.depth&&(be=_.stencil?t.DEPTH24_STENCIL8:t.DEPTH_COMPONENT24,le=_.stencil?Pr:Ds,_e=_.stencil?Ls:Xi);const Te={colorFormat:t.RGBA8,depthFormat:be,scaleFactor:r};f=new XRWebGLBinding(s,t),h=f.createProjectionLayer(Te),s.updateRenderState({layers:[h]}),e.setPixelRatio(1),e.setSize(h.textureWidth,h.textureHeight,!1),p=new Bs(h.textureWidth,h.textureHeight,{format:Xn,type:es,depthTexture:new um(h.textureWidth,h.textureHeight,_e,void 0,void 0,void 0,void 0,void 0,void 0,le),stencilBuffer:_.stencil,colorSpace:e.outputColorSpace,samples:_.antialias?4:0});const Ue=e.properties.get(p);Ue.__ignoreDepthValues=h.ignoreDepthValues}p.isXRRenderTarget=!0,this.setFoveation(l),c=null,o=await s.requestReferenceSpace(a),re.setContext(s),re.start(),n.isPresenting=!0,n.dispatchEvent({type:"sessionstart"})}},this.getEnvironmentBlendMode=function(){if(s!==null)return s.environmentBlendMode};function O(Q){for(let le=0;le<Q.removed.length;le++){const _e=Q.removed[le],be=y.indexOf(_e);be>=0&&(y[be]=null,x[be].disconnect(_e))}for(let le=0;le<Q.added.length;le++){const _e=Q.added[le];let be=y.indexOf(_e);if(be===-1){for(let Ue=0;Ue<x.length;Ue++)if(Ue>=y.length){y.push(_e),be=Ue;break}else if(y[Ue]===null){y[Ue]=_e,be=Ue;break}if(be===-1)break}const Te=x[be];Te&&Te.connect(_e)}}const k=new $,H=new $;function q(Q,le,_e){k.setFromMatrixPosition(le.matrixWorld),H.setFromMatrixPosition(_e.matrixWorld);const be=k.distanceTo(H),Te=le.projectionMatrix.elements,Ue=_e.projectionMatrix.elements,Ie=Te[14]/(Te[10]-1),Se=Te[14]/(Te[10]+1),Ke=(Te[9]+1)/Te[5],E=(Te[9]-1)/Te[5],z=(Te[8]-1)/Te[0],V=(Ue[8]+1)/Ue[0],te=Ie*z,K=Ie*V,oe=be/(-z+V),ae=oe*-z;le.matrixWorld.decompose(Q.position,Q.quaternion,Q.scale),Q.translateX(ae),Q.translateZ(oe),Q.matrixWorld.compose(Q.position,Q.quaternion,Q.scale),Q.matrixWorldInverse.copy(Q.matrixWorld).invert();const T=Ie+oe,M=Se+oe,U=te-ae,ee=K+(be-ae),X=Ke*Se/M*T,J=E*Se/M*T;Q.projectionMatrix.makePerspective(U,ee,X,J,T,M),Q.projectionMatrixInverse.copy(Q.projectionMatrix).invert()}function Z(Q,le){le===null?Q.matrixWorld.copy(Q.matrix):Q.matrixWorld.multiplyMatrices(le.matrixWorld,Q.matrix),Q.matrixWorldInverse.copy(Q.matrixWorld).invert()}this.updateCamera=function(Q){if(s===null)return;v.near=w.near=L.near=Q.near,v.far=w.far=L.far=Q.far,(b!==v.near||N!==v.far)&&(s.updateRenderState({depthNear:v.near,depthFar:v.far}),b=v.near,N=v.far);const le=Q.parent,_e=v.cameras;Z(v,le);for(let be=0;be<_e.length;be++)Z(_e[be],le);_e.length===2?q(v,L,w):v.projectionMatrix.copy(L.projectionMatrix),W(Q,v,le)};function W(Q,le,_e){_e===null?Q.matrix.copy(le.matrixWorld):(Q.matrix.copy(_e.matrixWorld),Q.matrix.invert(),Q.matrix.multiply(le.matrixWorld)),Q.matrix.decompose(Q.position,Q.quaternion,Q.scale),Q.updateMatrixWorld(!0),Q.projectionMatrix.copy(le.projectionMatrix),Q.projectionMatrixInverse.copy(le.projectionMatrixInverse),Q.isPerspectiveCamera&&(Q.fov=Hc*2*Math.atan(1/Q.projectionMatrix.elements[5]),Q.zoom=1)}this.getCamera=function(){return v},this.getFoveation=function(){if(!(h===null&&d===null))return l},this.setFoveation=function(Q){l=Q,h!==null&&(h.fixedFoveation=Q),d!==null&&d.fixedFoveation!==void 0&&(d.fixedFoveation=Q)};let j=null;function G(Q,le){if(u=le.getViewerPose(c||o),g=le,u!==null){const _e=u.views;d!==null&&(e.setRenderTargetFramebuffer(p,d.framebuffer),e.setRenderTarget(p));let be=!1;_e.length!==v.cameras.length&&(v.cameras.length=0,be=!0);for(let Te=0;Te<_e.length;Te++){const Ue=_e[Te];let Ie=null;if(d!==null)Ie=d.getViewport(Ue);else{const Ke=f.getViewSubImage(h,Ue);Ie=Ke.viewport,Te===0&&(e.setRenderTargetTextures(p,Ke.colorTexture,h.ignoreDepthValues?void 0:Ke.depthStencilTexture),e.setRenderTarget(p))}let Se=B[Te];Se===void 0&&(Se=new Un,Se.layers.enable(Te),Se.viewport=new Ft,B[Te]=Se),Se.matrix.fromArray(Ue.transform.matrix),Se.matrix.decompose(Se.position,Se.quaternion,Se.scale),Se.projectionMatrix.fromArray(Ue.projectionMatrix),Se.projectionMatrixInverse.copy(Se.projectionMatrix).invert(),Se.viewport.set(Ie.x,Ie.y,Ie.width,Ie.height),Te===0&&(v.matrix.copy(Se.matrix),v.matrix.decompose(v.position,v.quaternion,v.scale)),be===!0&&v.cameras.push(Se)}}for(let _e=0;_e<x.length;_e++){const be=y[_e],Te=x[_e];be!==null&&Te!==void 0&&Te.update(be,le,c||o)}j&&j(Q,le),le.detectedPlanes&&n.dispatchEvent({type:"planesdetected",data:le}),g=null}const re=new lm;re.setAnimationLoop(G),this.setAnimationLoop=function(Q){j=Q},this.dispose=function(){}}}function eb(i,e){function t(m,p){m.matrixAutoUpdate===!0&&m.updateMatrix(),p.value.copy(m.matrix)}function n(m,p){p.color.getRGB(m.fogColor.value,rm(i)),p.isFog?(m.fogNear.value=p.near,m.fogFar.value=p.far):p.isFogExp2&&(m.fogDensity.value=p.density)}function s(m,p,x,y,S){p.isMeshBasicMaterial||p.isMeshLambertMaterial?r(m,p):p.isMeshToonMaterial?(r(m,p),f(m,p)):p.isMeshPhongMaterial?(r(m,p),u(m,p)):p.isMeshStandardMaterial?(r(m,p),h(m,p),p.isMeshPhysicalMaterial&&d(m,p,S)):p.isMeshMatcapMaterial?(r(m,p),g(m,p)):p.isMeshDepthMaterial?r(m,p):p.isMeshDistanceMaterial?(r(m,p),_(m,p)):p.isMeshNormalMaterial?r(m,p):p.isLineBasicMaterial?(o(m,p),p.isLineDashedMaterial&&a(m,p)):p.isPointsMaterial?l(m,p,x,y):p.isSpriteMaterial?c(m,p):p.isShadowMaterial?(m.color.value.copy(p.color),m.opacity.value=p.opacity):p.isShaderMaterial&&(p.uniformsNeedUpdate=!1)}function r(m,p){m.opacity.value=p.opacity,p.color&&m.diffuse.value.copy(p.color),p.emissive&&m.emissive.value.copy(p.emissive).multiplyScalar(p.emissiveIntensity),p.map&&(m.map.value=p.map,t(p.map,m.mapTransform)),p.alphaMap&&(m.alphaMap.value=p.alphaMap,t(p.alphaMap,m.alphaMapTransform)),p.bumpMap&&(m.bumpMap.value=p.bumpMap,t(p.bumpMap,m.bumpMapTransform),m.bumpScale.value=p.bumpScale,p.side===un&&(m.bumpScale.value*=-1)),p.normalMap&&(m.normalMap.value=p.normalMap,t(p.normalMap,m.normalMapTransform),m.normalScale.value.copy(p.normalScale),p.side===un&&m.normalScale.value.negate()),p.displacementMap&&(m.displacementMap.value=p.displacementMap,t(p.displacementMap,m.displacementMapTransform),m.displacementScale.value=p.displacementScale,m.displacementBias.value=p.displacementBias),p.emissiveMap&&(m.emissiveMap.value=p.emissiveMap,t(p.emissiveMap,m.emissiveMapTransform)),p.specularMap&&(m.specularMap.value=p.specularMap,t(p.specularMap,m.specularMapTransform)),p.alphaTest>0&&(m.alphaTest.value=p.alphaTest);const x=e.get(p).envMap;if(x&&(m.envMap.value=x,m.flipEnvMap.value=x.isCubeTexture&&x.isRenderTargetTexture===!1?-1:1,m.reflectivity.value=p.reflectivity,m.ior.value=p.ior,m.refractionRatio.value=p.refractionRatio),p.lightMap){m.lightMap.value=p.lightMap;const y=i._useLegacyLights===!0?Math.PI:1;m.lightMapIntensity.value=p.lightMapIntensity*y,t(p.lightMap,m.lightMapTransform)}p.aoMap&&(m.aoMap.value=p.aoMap,m.aoMapIntensity.value=p.aoMapIntensity,t(p.aoMap,m.aoMapTransform))}function o(m,p){m.diffuse.value.copy(p.color),m.opacity.value=p.opacity,p.map&&(m.map.value=p.map,t(p.map,m.mapTransform))}function a(m,p){m.dashSize.value=p.dashSize,m.totalSize.value=p.dashSize+p.gapSize,m.scale.value=p.scale}function l(m,p,x,y){m.diffuse.value.copy(p.color),m.opacity.value=p.opacity,m.size.value=p.size*x,m.scale.value=y*.5,p.map&&(m.map.value=p.map,t(p.map,m.uvTransform)),p.alphaMap&&(m.alphaMap.value=p.alphaMap,t(p.alphaMap,m.alphaMapTransform)),p.alphaTest>0&&(m.alphaTest.value=p.alphaTest)}function c(m,p){m.diffuse.value.copy(p.color),m.opacity.value=p.opacity,m.rotation.value=p.rotation,p.map&&(m.map.value=p.map,t(p.map,m.mapTransform)),p.alphaMap&&(m.alphaMap.value=p.alphaMap,t(p.alphaMap,m.alphaMapTransform)),p.alphaTest>0&&(m.alphaTest.value=p.alphaTest)}function u(m,p){m.specular.value.copy(p.specular),m.shininess.value=Math.max(p.shininess,1e-4)}function f(m,p){p.gradientMap&&(m.gradientMap.value=p.gradientMap)}function h(m,p){m.metalness.value=p.metalness,p.metalnessMap&&(m.metalnessMap.value=p.metalnessMap,t(p.metalnessMap,m.metalnessMapTransform)),m.roughness.value=p.roughness,p.roughnessMap&&(m.roughnessMap.value=p.roughnessMap,t(p.roughnessMap,m.roughnessMapTransform)),e.get(p).envMap&&(m.envMapIntensity.value=p.envMapIntensity)}function d(m,p,x){m.ior.value=p.ior,p.sheen>0&&(m.sheenColor.value.copy(p.sheenColor).multiplyScalar(p.sheen),m.sheenRoughness.value=p.sheenRoughness,p.sheenColorMap&&(m.sheenColorMap.value=p.sheenColorMap,t(p.sheenColorMap,m.sheenColorMapTransform)),p.sheenRoughnessMap&&(m.sheenRoughnessMap.value=p.sheenRoughnessMap,t(p.sheenRoughnessMap,m.sheenRoughnessMapTransform))),p.clearcoat>0&&(m.clearcoat.value=p.clearcoat,m.clearcoatRoughness.value=p.clearcoatRoughness,p.clearcoatMap&&(m.clearcoatMap.value=p.clearcoatMap,t(p.clearcoatMap,m.clearcoatMapTransform)),p.clearcoatRoughnessMap&&(m.clearcoatRoughnessMap.value=p.clearcoatRoughnessMap,t(p.clearcoatRoughnessMap,m.clearcoatRoughnessMapTransform)),p.clearcoatNormalMap&&(m.clearcoatNormalMap.value=p.clearcoatNormalMap,t(p.clearcoatNormalMap,m.clearcoatNormalMapTransform),m.clearcoatNormalScale.value.copy(p.clearcoatNormalScale),p.side===un&&m.clearcoatNormalScale.value.negate())),p.iridescence>0&&(m.iridescence.value=p.iridescence,m.iridescenceIOR.value=p.iridescenceIOR,m.iridescenceThicknessMinimum.value=p.iridescenceThicknessRange[0],m.iridescenceThicknessMaximum.value=p.iridescenceThicknessRange[1],p.iridescenceMap&&(m.iridescenceMap.value=p.iridescenceMap,t(p.iridescenceMap,m.iridescenceMapTransform)),p.iridescenceThicknessMap&&(m.iridescenceThicknessMap.value=p.iridescenceThicknessMap,t(p.iridescenceThicknessMap,m.iridescenceThicknessMapTransform))),p.transmission>0&&(m.transmission.value=p.transmission,m.transmissionSamplerMap.value=x.texture,m.transmissionSamplerSize.value.set(x.width,x.height),p.transmissionMap&&(m.transmissionMap.value=p.transmissionMap,t(p.transmissionMap,m.transmissionMapTransform)),m.thickness.value=p.thickness,p.thicknessMap&&(m.thicknessMap.value=p.thicknessMap,t(p.thicknessMap,m.thicknessMapTransform)),m.attenuationDistance.value=p.attenuationDistance,m.attenuationColor.value.copy(p.attenuationColor)),p.anisotropy>0&&(m.anisotropyVector.value.set(p.anisotropy*Math.cos(p.anisotropyRotation),p.anisotropy*Math.sin(p.anisotropyRotation)),p.anisotropyMap&&(m.anisotropyMap.value=p.anisotropyMap,t(p.anisotropyMap,m.anisotropyMapTransform))),m.specularIntensity.value=p.specularIntensity,m.specularColor.value.copy(p.specularColor),p.specularColorMap&&(m.specularColorMap.value=p.specularColorMap,t(p.specularColorMap,m.specularColorMapTransform)),p.specularIntensityMap&&(m.specularIntensityMap.value=p.specularIntensityMap,t(p.specularIntensityMap,m.specularIntensityMapTransform))}function g(m,p){p.matcap&&(m.matcap.value=p.matcap)}function _(m,p){const x=e.get(p).light;m.referencePosition.value.setFromMatrixPosition(x.matrixWorld),m.nearDistance.value=x.shadow.camera.near,m.farDistance.value=x.shadow.camera.far}return{refreshFogUniforms:n,refreshMaterialUniforms:s}}function tb(i,e,t,n){let s={},r={},o=[];const a=t.isWebGL2?i.getParameter(i.MAX_UNIFORM_BUFFER_BINDINGS):0;function l(x,y){const S=y.program;n.uniformBlockBinding(x,S)}function c(x,y){let S=s[x.id];S===void 0&&(g(x),S=u(x),s[x.id]=S,x.addEventListener("dispose",m));const R=y.program;n.updateUBOMapping(x,R);const L=e.render.frame;r[x.id]!==L&&(h(x),r[x.id]=L)}function u(x){const y=f();x.__bindingPointIndex=y;const S=i.createBuffer(),R=x.__size,L=x.usage;return i.bindBuffer(i.UNIFORM_BUFFER,S),i.bufferData(i.UNIFORM_BUFFER,R,L),i.bindBuffer(i.UNIFORM_BUFFER,null),i.bindBufferBase(i.UNIFORM_BUFFER,y,S),S}function f(){for(let x=0;x<a;x++)if(o.indexOf(x)===-1)return o.push(x),x;return console.error("THREE.WebGLRenderer: Maximum number of simultaneously usable uniforms groups reached."),0}function h(x){const y=s[x.id],S=x.uniforms,R=x.__cache;i.bindBuffer(i.UNIFORM_BUFFER,y);for(let L=0,w=S.length;L<w;L++){const B=Array.isArray(S[L])?S[L]:[S[L]];for(let v=0,b=B.length;v<b;v++){const N=B[v];if(d(N,L,v,R)===!0){const A=N.__offset,I=Array.isArray(N.value)?N.value:[N.value];let O=0;for(let k=0;k<I.length;k++){const H=I[k],q=_(H);typeof H=="number"||typeof H=="boolean"?(N.__data[0]=H,i.bufferSubData(i.UNIFORM_BUFFER,A+O,N.__data)):H.isMatrix3?(N.__data[0]=H.elements[0],N.__data[1]=H.elements[1],N.__data[2]=H.elements[2],N.__data[3]=0,N.__data[4]=H.elements[3],N.__data[5]=H.elements[4],N.__data[6]=H.elements[5],N.__data[7]=0,N.__data[8]=H.elements[6],N.__data[9]=H.elements[7],N.__data[10]=H.elements[8],N.__data[11]=0):(H.toArray(N.__data,O),O+=q.storage/Float32Array.BYTES_PER_ELEMENT)}i.bufferSubData(i.UNIFORM_BUFFER,A,N.__data)}}}i.bindBuffer(i.UNIFORM_BUFFER,null)}function d(x,y,S,R){const L=x.value,w=y+"_"+S;if(R[w]===void 0)return typeof L=="number"||typeof L=="boolean"?R[w]=L:R[w]=L.clone(),!0;{const B=R[w];if(typeof L=="number"||typeof L=="boolean"){if(B!==L)return R[w]=L,!0}else if(B.equals(L)===!1)return B.copy(L),!0}return!1}function g(x){const y=x.uniforms;let S=0;const R=16;for(let w=0,B=y.length;w<B;w++){const v=Array.isArray(y[w])?y[w]:[y[w]];for(let b=0,N=v.length;b<N;b++){const A=v[b],I=Array.isArray(A.value)?A.value:[A.value];for(let O=0,k=I.length;O<k;O++){const H=I[O],q=_(H),Z=S%R;Z!==0&&R-Z<q.boundary&&(S+=R-Z),A.__data=new Float32Array(q.storage/Float32Array.BYTES_PER_ELEMENT),A.__offset=S,S+=q.storage}}}const L=S%R;return L>0&&(S+=R-L),x.__size=S,x.__cache={},this}function _(x){const y={boundary:0,storage:0};return typeof x=="number"||typeof x=="boolean"?(y.boundary=4,y.storage=4):x.isVector2?(y.boundary=8,y.storage=8):x.isVector3||x.isColor?(y.boundary=16,y.storage=12):x.isVector4?(y.boundary=16,y.storage=16):x.isMatrix3?(y.boundary=48,y.storage=48):x.isMatrix4?(y.boundary=64,y.storage=64):x.isTexture?console.warn("THREE.WebGLRenderer: Texture samplers can not be part of an uniforms group."):console.warn("THREE.WebGLRenderer: Unsupported uniform value type.",x),y}function m(x){const y=x.target;y.removeEventListener("dispose",m);const S=o.indexOf(y.__bindingPointIndex);o.splice(S,1),i.deleteBuffer(s[y.id]),delete s[y.id],delete r[y.id]}function p(){for(const x in s)i.deleteBuffer(s[x]);o=[],s={},r={}}return{bind:l,update:c,dispose:p}}class _m{constructor(e={}){const{canvas:t=Zv(),context:n=null,depth:s=!0,stencil:r=!0,alpha:o=!1,antialias:a=!1,premultipliedAlpha:l=!0,preserveDrawingBuffer:c=!1,powerPreference:u="default",failIfMajorPerformanceCaveat:f=!1}=e;this.isWebGLRenderer=!0;let h;n!==null?h=n.getContextAttributes().alpha:h=o;const d=new Uint32Array(4),g=new Int32Array(4);let _=null,m=null;const p=[],x=[];this.domElement=t,this.debug={checkShaderErrors:!0,onShaderError:null},this.autoClear=!0,this.autoClearColor=!0,this.autoClearDepth=!0,this.autoClearStencil=!0,this.sortObjects=!0,this.clippingPlanes=[],this.localClippingEnabled=!1,this._outputColorSpace=kt,this._useLegacyLights=!1,this.toneMapping=Qi,this.toneMappingExposure=1;const y=this;let S=!1,R=0,L=0,w=null,B=-1,v=null;const b=new Ft,N=new Ft;let A=null;const I=new Qe(0);let O=0,k=t.width,H=t.height,q=1,Z=null,W=null;const j=new Ft(0,0,k,H),G=new Ft(0,0,k,H);let re=!1;const Q=new Ru;let le=!1,_e=!1,be=null;const Te=new Lt,Ue=new He,Ie=new $,Se={background:null,fog:null,environment:null,overrideMaterial:null,isScene:!0};function Ke(){return w===null?q:1}let E=n;function z(P,Y){for(let ie=0;ie<P.length;ie++){const se=P[ie],ne=t.getContext(se,Y);if(ne!==null)return ne}return null}try{const P={alpha:!0,depth:s,stencil:r,antialias:a,premultipliedAlpha:l,preserveDrawingBuffer:c,powerPreference:u,failIfMajorPerformanceCaveat:f};if("setAttribute"in t&&t.setAttribute("data-engine",`three.js r${bu}`),t.addEventListener("webglcontextlost",he,!1),t.addEventListener("webglcontextrestored",F,!1),t.addEventListener("webglcontextcreationerror",me,!1),E===null){const Y=["webgl2","webgl","experimental-webgl"];if(y.isWebGL1Renderer===!0&&Y.shift(),E=z(Y,P),E===null)throw z(Y)?new Error("Error creating WebGL context with your selected attributes."):new Error("Error creating WebGL context.")}typeof WebGLRenderingContext<"u"&&E instanceof WebGLRenderingContext&&console.warn("THREE.WebGLRenderer: WebGL 1 support was deprecated in r153 and will be removed in r163."),E.getShaderPrecisionFormat===void 0&&(E.getShaderPrecisionFormat=function(){return{rangeMin:1,rangeMax:1,precision:1}})}catch(P){throw console.error("THREE.WebGLRenderer: "+P.message),P}let V,te,K,oe,ae,T,M,U,ee,X,J,fe,ue,de,xe,Ae,ce,ke,De,Le,Re,ge,D,pe;function we(){V=new fM(E),te=new rM(E,V,e),V.init(te),ge=new KE(E,V,te),K=new $E(E,V,te),oe=new pM(E),ae=new IE,T=new jE(E,V,K,ae,te,ge,oe),M=new aM(y),U=new uM(y),ee=new Mx(E,te),D=new iM(E,V,ee,te),X=new hM(E,ee,oe,D),J=new vM(E,X,ee,oe),De=new gM(E,te,T),Ae=new oM(ae),fe=new UE(y,M,U,V,te,D,Ae),ue=new eb(y,ae),de=new NE,xe=new HE(V,te),ke=new nM(y,M,U,K,J,h,l),ce=new YE(y,J,te),pe=new tb(E,oe,te,K),Le=new sM(E,V,oe,te),Re=new dM(E,V,oe,te),oe.programs=fe.programs,y.capabilities=te,y.extensions=V,y.properties=ae,y.renderLists=de,y.shadowMap=ce,y.state=K,y.info=oe}we();const Ee=new QE(y,E);this.xr=Ee,this.getContext=function(){return E},this.getContextAttributes=function(){return E.getContextAttributes()},this.forceContextLoss=function(){const P=V.get("WEBGL_lose_context");P&&P.loseContext()},this.forceContextRestore=function(){const P=V.get("WEBGL_lose_context");P&&P.restoreContext()},this.getPixelRatio=function(){return q},this.setPixelRatio=function(P){P!==void 0&&(q=P,this.setSize(k,H,!1))},this.getSize=function(P){return P.set(k,H)},this.setSize=function(P,Y,ie=!0){if(Ee.isPresenting){console.warn("THREE.WebGLRenderer: Can't change size while VR device is presenting.");return}k=P,H=Y,t.width=Math.floor(P*q),t.height=Math.floor(Y*q),ie===!0&&(t.style.width=P+"px",t.style.height=Y+"px"),this.setViewport(0,0,P,Y)},this.getDrawingBufferSize=function(P){return P.set(k*q,H*q).floor()},this.setDrawingBufferSize=function(P,Y,ie){k=P,H=Y,q=ie,t.width=Math.floor(P*ie),t.height=Math.floor(Y*ie),this.setViewport(0,0,P,Y)},this.getCurrentViewport=function(P){return P.copy(b)},this.getViewport=function(P){return P.copy(j)},this.setViewport=function(P,Y,ie,se){P.isVector4?j.set(P.x,P.y,P.z,P.w):j.set(P,Y,ie,se),K.viewport(b.copy(j).multiplyScalar(q).floor())},this.getScissor=function(P){return P.copy(G)},this.setScissor=function(P,Y,ie,se){P.isVector4?G.set(P.x,P.y,P.z,P.w):G.set(P,Y,ie,se),K.scissor(N.copy(G).multiplyScalar(q).floor())},this.getScissorTest=function(){return re},this.setScissorTest=function(P){K.setScissorTest(re=P)},this.setOpaqueSort=function(P){Z=P},this.setTransparentSort=function(P){W=P},this.getClearColor=function(P){return P.copy(ke.getClearColor())},this.setClearColor=function(){ke.setClearColor.apply(ke,arguments)},this.getClearAlpha=function(){return ke.getClearAlpha()},this.setClearAlpha=function(){ke.setClearAlpha.apply(ke,arguments)},this.clear=function(P=!0,Y=!0,ie=!0){let se=0;if(P){let ne=!1;if(w!==null){const Me=w.texture.format;ne=Me===Yp||Me===qp||Me===Xp}if(ne){const Me=w.texture.type,Ce=Me===es||Me===Xi||Me===Tu||Me===Ls||Me===Gp||Me===Wp,Ne=ke.getClearColor(),Be=ke.getClearAlpha(),qe=Ne.r,Ve=Ne.g,Ge=Ne.b;Ce?(d[0]=qe,d[1]=Ve,d[2]=Ge,d[3]=Be,E.clearBufferuiv(E.COLOR,0,d)):(g[0]=qe,g[1]=Ve,g[2]=Ge,g[3]=Be,E.clearBufferiv(E.COLOR,0,g))}else se|=E.COLOR_BUFFER_BIT}Y&&(se|=E.DEPTH_BUFFER_BIT),ie&&(se|=E.STENCIL_BUFFER_BIT,this.state.buffers.stencil.setMask(4294967295)),E.clear(se)},this.clearColor=function(){this.clear(!0,!1,!1)},this.clearDepth=function(){this.clear(!1,!0,!1)},this.clearStencil=function(){this.clear(!1,!1,!0)},this.dispose=function(){t.removeEventListener("webglcontextlost",he,!1),t.removeEventListener("webglcontextrestored",F,!1),t.removeEventListener("webglcontextcreationerror",me,!1),de.dispose(),xe.dispose(),ae.dispose(),M.dispose(),U.dispose(),J.dispose(),D.dispose(),pe.dispose(),fe.dispose(),Ee.dispose(),Ee.removeEventListener("sessionstart",Tt),Ee.removeEventListener("sessionend",nt),be&&(be.dispose(),be=null),Rt.stop()};function he(P){P.preventDefault(),console.log("THREE.WebGLRenderer: Context Lost."),S=!0}function F(){console.log("THREE.WebGLRenderer: Context Restored."),S=!1;const P=oe.autoReset,Y=ce.enabled,ie=ce.autoUpdate,se=ce.needsUpdate,ne=ce.type;we(),oe.autoReset=P,ce.enabled=Y,ce.autoUpdate=ie,ce.needsUpdate=se,ce.type=ne}function me(P){console.error("THREE.WebGLRenderer: A WebGL context could not be created. Reason: ",P.statusMessage)}function ye(P){const Y=P.target;Y.removeEventListener("dispose",ye),Oe(Y)}function Oe(P){Pe(P),ae.remove(P)}function Pe(P){const Y=ae.get(P).programs;Y!==void 0&&(Y.forEach(function(ie){fe.releaseProgram(ie)}),P.isShaderMaterial&&fe.releaseShaderCache(P))}this.renderBufferDirect=function(P,Y,ie,se,ne,Me){Y===null&&(Y=Se);const Ce=ne.isMesh&&ne.matrixWorld.determinant()<0,Ne=M_(P,Y,ie,se,ne);K.setMaterial(se,Ce);let Be=ie.index,qe=1;if(se.wireframe===!0){if(Be=X.getWireframeAttribute(ie),Be===void 0)return;qe=2}const Ve=ie.drawRange,Ge=ie.attributes.position;let At=Ve.start*qe,_n=(Ve.start+Ve.count)*qe;Me!==null&&(At=Math.max(At,Me.start*qe),_n=Math.min(_n,(Me.start+Me.count)*qe)),Be!==null?(At=Math.max(At,0),_n=Math.min(_n,Be.count)):Ge!=null&&(At=Math.max(At,0),_n=Math.min(_n,Ge.count));const It=_n-At;if(It<0||It===1/0)return;D.setup(ne,se,Ne,ie,Be);let ci,gt=Le;if(Be!==null&&(ci=ee.get(Be),gt=Re,gt.setIndex(ci)),ne.isMesh)se.wireframe===!0?(K.setLineWidth(se.wireframeLinewidth*Ke()),gt.setMode(E.LINES)):gt.setMode(E.TRIANGLES);else if(ne.isLine){let Ye=se.linewidth;Ye===void 0&&(Ye=1),K.setLineWidth(Ye*Ke()),ne.isLineSegments?gt.setMode(E.LINES):ne.isLineLoop?gt.setMode(E.LINE_LOOP):gt.setMode(E.LINE_STRIP)}else ne.isPoints?gt.setMode(E.POINTS):ne.isSprite&&gt.setMode(E.TRIANGLES);if(ne.isBatchedMesh)gt.renderMultiDraw(ne._multiDrawStarts,ne._multiDrawCounts,ne._multiDrawCount);else if(ne.isInstancedMesh)gt.renderInstances(At,It,ne.count);else if(ie.isInstancedBufferGeometry){const Ye=ie._maxInstanceCount!==void 0?ie._maxInstanceCount:1/0,El=Math.min(ie.instanceCount,Ye);gt.renderInstances(At,It,El)}else gt.render(At,It)};function Ze(P,Y,ie){P.transparent===!0&&P.side===Ai&&P.forceSinglePass===!1?(P.side=un,P.needsUpdate=!0,Ho(P,Y,ie),P.side=ss,P.needsUpdate=!0,Ho(P,Y,ie),P.side=Ai):Ho(P,Y,ie)}this.compile=function(P,Y,ie=null){ie===null&&(ie=P),m=xe.get(ie),m.init(),x.push(m),ie.traverseVisible(function(ne){ne.isLight&&ne.layers.test(Y.layers)&&(m.pushLight(ne),ne.castShadow&&m.pushShadow(ne))}),P!==ie&&P.traverseVisible(function(ne){ne.isLight&&ne.layers.test(Y.layers)&&(m.pushLight(ne),ne.castShadow&&m.pushShadow(ne))}),m.setupLights(y._useLegacyLights);const se=new Set;return P.traverse(function(ne){const Me=ne.material;if(Me)if(Array.isArray(Me))for(let Ce=0;Ce<Me.length;Ce++){const Ne=Me[Ce];Ze(Ne,ie,ne),se.add(Ne)}else Ze(Me,ie,ne),se.add(Me)}),x.pop(),m=null,se},this.compileAsync=function(P,Y,ie=null){const se=this.compile(P,Y,ie);return new Promise(ne=>{function Me(){if(se.forEach(function(Ce){ae.get(Ce).currentProgram.isReady()&&se.delete(Ce)}),se.size===0){ne(P);return}setTimeout(Me,10)}V.get("KHR_parallel_shader_compile")!==null?Me():setTimeout(Me,10)})};let Je=null;function St(P){Je&&Je(P)}function Tt(){Rt.stop()}function nt(){Rt.start()}const Rt=new lm;Rt.setAnimationLoop(St),typeof self<"u"&&Rt.setContext(self),this.setAnimationLoop=function(P){Je=P,Ee.setAnimationLoop(P),P===null?Rt.stop():Rt.start()},Ee.addEventListener("sessionstart",Tt),Ee.addEventListener("sessionend",nt),this.render=function(P,Y){if(Y!==void 0&&Y.isCamera!==!0){console.error("THREE.WebGLRenderer.render: camera is not an instance of THREE.Camera.");return}if(S===!0)return;P.matrixWorldAutoUpdate===!0&&P.updateMatrixWorld(),Y.parent===null&&Y.matrixWorldAutoUpdate===!0&&Y.updateMatrixWorld(),Ee.enabled===!0&&Ee.isPresenting===!0&&(Ee.cameraAutoUpdate===!0&&Ee.updateCamera(Y),Y=Ee.getCamera()),P.isScene===!0&&P.onBeforeRender(y,P,Y,w),m=xe.get(P,x.length),m.init(),x.push(m),Te.multiplyMatrices(Y.projectionMatrix,Y.matrixWorldInverse),Q.setFromProjectionMatrix(Te),_e=this.localClippingEnabled,le=Ae.init(this.clippingPlanes,_e),_=de.get(P,p.length),_.init(),p.push(_),jn(P,Y,0,y.sortObjects),_.finish(),y.sortObjects===!0&&_.sort(Z,W),this.info.render.frame++,le===!0&&Ae.beginShadows();const ie=m.state.shadowsArray;if(ce.render(ie,P,Y),le===!0&&Ae.endShadows(),this.info.autoReset===!0&&this.info.reset(),ke.render(_,P),m.setupLights(y._useLegacyLights),Y.isArrayCamera){const se=Y.cameras;for(let ne=0,Me=se.length;ne<Me;ne++){const Ce=se[ne];Ju(_,P,Ce,Ce.viewport)}}else Ju(_,P,Y);w!==null&&(T.updateMultisampleRenderTarget(w),T.updateRenderTargetMipmap(w)),P.isScene===!0&&P.onAfterRender(y,P,Y),D.resetDefaultState(),B=-1,v=null,x.pop(),x.length>0?m=x[x.length-1]:m=null,p.pop(),p.length>0?_=p[p.length-1]:_=null};function jn(P,Y,ie,se){if(P.visible===!1)return;if(P.layers.test(Y.layers)){if(P.isGroup)ie=P.renderOrder;else if(P.isLOD)P.autoUpdate===!0&&P.update(Y);else if(P.isLight)m.pushLight(P),P.castShadow&&m.pushShadow(P);else if(P.isSprite){if(!P.frustumCulled||Q.intersectsSprite(P)){se&&Ie.setFromMatrixPosition(P.matrixWorld).applyMatrix4(Te);const Ce=J.update(P),Ne=P.material;Ne.visible&&_.push(P,Ce,Ne,ie,Ie.z,null)}}else if((P.isMesh||P.isLine||P.isPoints)&&(!P.frustumCulled||Q.intersectsObject(P))){const Ce=J.update(P),Ne=P.material;if(se&&(P.boundingSphere!==void 0?(P.boundingSphere===null&&P.computeBoundingSphere(),Ie.copy(P.boundingSphere.center)):(Ce.boundingSphere===null&&Ce.computeBoundingSphere(),Ie.copy(Ce.boundingSphere.center)),Ie.applyMatrix4(P.matrixWorld).applyMatrix4(Te)),Array.isArray(Ne)){const Be=Ce.groups;for(let qe=0,Ve=Be.length;qe<Ve;qe++){const Ge=Be[qe],At=Ne[Ge.materialIndex];At&&At.visible&&_.push(P,Ce,At,ie,Ie.z,Ge)}}else Ne.visible&&_.push(P,Ce,Ne,ie,Ie.z,null)}}const Me=P.children;for(let Ce=0,Ne=Me.length;Ce<Ne;Ce++)jn(Me[Ce],Y,ie,se)}function Ju(P,Y,ie,se){const ne=P.opaque,Me=P.transmissive,Ce=P.transparent;m.setupLightsView(ie),le===!0&&Ae.setGlobalState(y.clippingPlanes,ie),Me.length>0&&S_(ne,Me,Y,ie),se&&K.viewport(b.copy(se)),ne.length>0&&Vo(ne,Y,ie),Me.length>0&&Vo(Me,Y,ie),Ce.length>0&&Vo(Ce,Y,ie),K.buffers.depth.setTest(!0),K.buffers.depth.setMask(!0),K.buffers.color.setMask(!0),K.setPolygonOffset(!1)}function S_(P,Y,ie,se){if((ie.isScene===!0?ie.overrideMaterial:null)!==null)return;const Me=te.isWebGL2;be===null&&(be=new Bs(1,1,{generateMipmaps:!0,type:V.has("EXT_color_buffer_half_float")?So:es,minFilter:yo,samples:Me?4:0})),y.getDrawingBufferSize(Ue),Me?be.setSize(Ue.x,Ue.y):be.setSize(Gc(Ue.x),Gc(Ue.y));const Ce=y.getRenderTarget();y.setRenderTarget(be),y.getClearColor(I),O=y.getClearAlpha(),O<1&&y.setClearColor(16777215,.5),y.clear();const Ne=y.toneMapping;y.toneMapping=Qi,Vo(P,ie,se),T.updateMultisampleRenderTarget(be),T.updateRenderTargetMipmap(be);let Be=!1;for(let qe=0,Ve=Y.length;qe<Ve;qe++){const Ge=Y[qe],At=Ge.object,_n=Ge.geometry,It=Ge.material,ci=Ge.group;if(It.side===Ai&&At.layers.test(se.layers)){const gt=It.side;It.side=un,It.needsUpdate=!0,Qu(At,ie,se,_n,It,ci),It.side=gt,It.needsUpdate=!0,Be=!0}}Be===!0&&(T.updateMultisampleRenderTarget(be),T.updateRenderTargetMipmap(be)),y.setRenderTarget(Ce),y.setClearColor(I,O),y.toneMapping=Ne}function Vo(P,Y,ie){const se=Y.isScene===!0?Y.overrideMaterial:null;for(let ne=0,Me=P.length;ne<Me;ne++){const Ce=P[ne],Ne=Ce.object,Be=Ce.geometry,qe=se===null?Ce.material:se,Ve=Ce.group;Ne.layers.test(ie.layers)&&Qu(Ne,Y,ie,Be,qe,Ve)}}function Qu(P,Y,ie,se,ne,Me){P.onBeforeRender(y,Y,ie,se,ne,Me),P.modelViewMatrix.multiplyMatrices(ie.matrixWorldInverse,P.matrixWorld),P.normalMatrix.getNormalMatrix(P.modelViewMatrix),ne.onBeforeRender(y,Y,ie,se,P,Me),ne.transparent===!0&&ne.side===Ai&&ne.forceSinglePass===!1?(ne.side=un,ne.needsUpdate=!0,y.renderBufferDirect(ie,Y,se,ne,P,Me),ne.side=ss,ne.needsUpdate=!0,y.renderBufferDirect(ie,Y,se,ne,P,Me),ne.side=Ai):y.renderBufferDirect(ie,Y,se,ne,P,Me),P.onAfterRender(y,Y,ie,se,ne,Me)}function Ho(P,Y,ie){Y.isScene!==!0&&(Y=Se);const se=ae.get(P),ne=m.state.lights,Me=m.state.shadowsArray,Ce=ne.state.version,Ne=fe.getParameters(P,ne.state,Me,Y,ie),Be=fe.getProgramCacheKey(Ne);let qe=se.programs;se.environment=P.isMeshStandardMaterial?Y.environment:null,se.fog=Y.fog,se.envMap=(P.isMeshStandardMaterial?U:M).get(P.envMap||se.environment),qe===void 0&&(P.addEventListener("dispose",ye),qe=new Map,se.programs=qe);let Ve=qe.get(Be);if(Ve!==void 0){if(se.currentProgram===Ve&&se.lightsStateVersion===Ce)return tf(P,Ne),Ve}else Ne.uniforms=fe.getUniforms(P),P.onBuild(ie,Ne,y),P.onBeforeCompile(Ne,y),Ve=fe.acquireProgram(Ne,Be),qe.set(Be,Ve),se.uniforms=Ne.uniforms;const Ge=se.uniforms;return(!P.isShaderMaterial&&!P.isRawShaderMaterial||P.clipping===!0)&&(Ge.clippingPlanes=Ae.uniform),tf(P,Ne),se.needsLights=b_(P),se.lightsStateVersion=Ce,se.needsLights&&(Ge.ambientLightColor.value=ne.state.ambient,Ge.lightProbe.value=ne.state.probe,Ge.directionalLights.value=ne.state.directional,Ge.directionalLightShadows.value=ne.state.directionalShadow,Ge.spotLights.value=ne.state.spot,Ge.spotLightShadows.value=ne.state.spotShadow,Ge.rectAreaLights.value=ne.state.rectArea,Ge.ltc_1.value=ne.state.rectAreaLTC1,Ge.ltc_2.value=ne.state.rectAreaLTC2,Ge.pointLights.value=ne.state.point,Ge.pointLightShadows.value=ne.state.pointShadow,Ge.hemisphereLights.value=ne.state.hemi,Ge.directionalShadowMap.value=ne.state.directionalShadowMap,Ge.directionalShadowMatrix.value=ne.state.directionalShadowMatrix,Ge.spotShadowMap.value=ne.state.spotShadowMap,Ge.spotLightMatrix.value=ne.state.spotLightMatrix,Ge.spotLightMap.value=ne.state.spotLightMap,Ge.pointShadowMap.value=ne.state.pointShadowMap,Ge.pointShadowMatrix.value=ne.state.pointShadowMatrix),se.currentProgram=Ve,se.uniformsList=null,Ve}function ef(P){if(P.uniformsList===null){const Y=P.currentProgram.getUniforms();P.uniformsList=wa.seqWithValue(Y.seq,P.uniforms)}return P.uniformsList}function tf(P,Y){const ie=ae.get(P);ie.outputColorSpace=Y.outputColorSpace,ie.batching=Y.batching,ie.instancing=Y.instancing,ie.instancingColor=Y.instancingColor,ie.skinning=Y.skinning,ie.morphTargets=Y.morphTargets,ie.morphNormals=Y.morphNormals,ie.morphColors=Y.morphColors,ie.morphTargetsCount=Y.morphTargetsCount,ie.numClippingPlanes=Y.numClippingPlanes,ie.numIntersection=Y.numClipIntersection,ie.vertexAlphas=Y.vertexAlphas,ie.vertexTangents=Y.vertexTangents,ie.toneMapping=Y.toneMapping}function M_(P,Y,ie,se,ne){Y.isScene!==!0&&(Y=Se),T.resetTextureUnits();const Me=Y.fog,Ce=se.isMeshStandardMaterial?Y.environment:null,Ne=w===null?y.outputColorSpace:w.isXRRenderTarget===!0?w.texture.colorSpace:Di,Be=(se.isMeshStandardMaterial?U:M).get(se.envMap||Ce),qe=se.vertexColors===!0&&!!ie.attributes.color&&ie.attributes.color.itemSize===4,Ve=!!ie.attributes.tangent&&(!!se.normalMap||se.anisotropy>0),Ge=!!ie.morphAttributes.position,At=!!ie.morphAttributes.normal,_n=!!ie.morphAttributes.color;let It=Qi;se.toneMapped&&(w===null||w.isXRRenderTarget===!0)&&(It=y.toneMapping);const ci=ie.morphAttributes.position||ie.morphAttributes.normal||ie.morphAttributes.color,gt=ci!==void 0?ci.length:0,Ye=ae.get(se),El=m.state.lights;if(le===!0&&(_e===!0||P!==v)){const Cn=P===v&&se.id===B;Ae.setState(se,P,Cn)}let Mt=!1;se.version===Ye.__version?(Ye.needsLights&&Ye.lightsStateVersion!==El.state.version||Ye.outputColorSpace!==Ne||ne.isBatchedMesh&&Ye.batching===!1||!ne.isBatchedMesh&&Ye.batching===!0||ne.isInstancedMesh&&Ye.instancing===!1||!ne.isInstancedMesh&&Ye.instancing===!0||ne.isSkinnedMesh&&Ye.skinning===!1||!ne.isSkinnedMesh&&Ye.skinning===!0||ne.isInstancedMesh&&Ye.instancingColor===!0&&ne.instanceColor===null||ne.isInstancedMesh&&Ye.instancingColor===!1&&ne.instanceColor!==null||Ye.envMap!==Be||se.fog===!0&&Ye.fog!==Me||Ye.numClippingPlanes!==void 0&&(Ye.numClippingPlanes!==Ae.numPlanes||Ye.numIntersection!==Ae.numIntersection)||Ye.vertexAlphas!==qe||Ye.vertexTangents!==Ve||Ye.morphTargets!==Ge||Ye.morphNormals!==At||Ye.morphColors!==_n||Ye.toneMapping!==It||te.isWebGL2===!0&&Ye.morphTargetsCount!==gt)&&(Mt=!0):(Mt=!0,Ye.__version=se.version);let us=Ye.currentProgram;Mt===!0&&(us=Ho(se,Y,ne));let nf=!1,kr=!1,bl=!1;const Gt=us.getUniforms(),fs=Ye.uniforms;if(K.useProgram(us.program)&&(nf=!0,kr=!0,bl=!0),se.id!==B&&(B=se.id,kr=!0),nf||v!==P){Gt.setValue(E,"projectionMatrix",P.projectionMatrix),Gt.setValue(E,"viewMatrix",P.matrixWorldInverse);const Cn=Gt.map.cameraPosition;Cn!==void 0&&Cn.setValue(E,Ie.setFromMatrixPosition(P.matrixWorld)),te.logarithmicDepthBuffer&&Gt.setValue(E,"logDepthBufFC",2/(Math.log(P.far+1)/Math.LN2)),(se.isMeshPhongMaterial||se.isMeshToonMaterial||se.isMeshLambertMaterial||se.isMeshBasicMaterial||se.isMeshStandardMaterial||se.isShaderMaterial)&&Gt.setValue(E,"isOrthographic",P.isOrthographicCamera===!0),v!==P&&(v=P,kr=!0,bl=!0)}if(ne.isSkinnedMesh){Gt.setOptional(E,ne,"bindMatrix"),Gt.setOptional(E,ne,"bindMatrixInverse");const Cn=ne.skeleton;Cn&&(te.floatVertexTextures?(Cn.boneTexture===null&&Cn.computeBoneTexture(),Gt.setValue(E,"boneTexture",Cn.boneTexture,T)):console.warn("THREE.WebGLRenderer: SkinnedMesh can only be used with WebGL 2. With WebGL 1 OES_texture_float and vertex textures support is required."))}ne.isBatchedMesh&&(Gt.setOptional(E,ne,"batchingTexture"),Gt.setValue(E,"batchingTexture",ne._matricesTexture,T));const Tl=ie.morphAttributes;if((Tl.position!==void 0||Tl.normal!==void 0||Tl.color!==void 0&&te.isWebGL2===!0)&&De.update(ne,ie,us),(kr||Ye.receiveShadow!==ne.receiveShadow)&&(Ye.receiveShadow=ne.receiveShadow,Gt.setValue(E,"receiveShadow",ne.receiveShadow)),se.isMeshGouraudMaterial&&se.envMap!==null&&(fs.envMap.value=Be,fs.flipEnvMap.value=Be.isCubeTexture&&Be.isRenderTargetTexture===!1?-1:1),kr&&(Gt.setValue(E,"toneMappingExposure",y.toneMappingExposure),Ye.needsLights&&E_(fs,bl),Me&&se.fog===!0&&ue.refreshFogUniforms(fs,Me),ue.refreshMaterialUniforms(fs,se,q,H,be),wa.upload(E,ef(Ye),fs,T)),se.isShaderMaterial&&se.uniformsNeedUpdate===!0&&(wa.upload(E,ef(Ye),fs,T),se.uniformsNeedUpdate=!1),se.isSpriteMaterial&&Gt.setValue(E,"center",ne.center),Gt.setValue(E,"modelViewMatrix",ne.modelViewMatrix),Gt.setValue(E,"normalMatrix",ne.normalMatrix),Gt.setValue(E,"modelMatrix",ne.matrixWorld),se.isShaderMaterial||se.isRawShaderMaterial){const Cn=se.uniformsGroups;for(let Al=0,T_=Cn.length;Al<T_;Al++)if(te.isWebGL2){const sf=Cn[Al];pe.update(sf,us),pe.bind(sf,us)}else console.warn("THREE.WebGLRenderer: Uniform Buffer Objects can only be used with WebGL 2.")}return us}function E_(P,Y){P.ambientLightColor.needsUpdate=Y,P.lightProbe.needsUpdate=Y,P.directionalLights.needsUpdate=Y,P.directionalLightShadows.needsUpdate=Y,P.pointLights.needsUpdate=Y,P.pointLightShadows.needsUpdate=Y,P.spotLights.needsUpdate=Y,P.spotLightShadows.needsUpdate=Y,P.rectAreaLights.needsUpdate=Y,P.hemisphereLights.needsUpdate=Y}function b_(P){return P.isMeshLambertMaterial||P.isMeshToonMaterial||P.isMeshPhongMaterial||P.isMeshStandardMaterial||P.isShadowMaterial||P.isShaderMaterial&&P.lights===!0}this.getActiveCubeFace=function(){return R},this.getActiveMipmapLevel=function(){return L},this.getRenderTarget=function(){return w},this.setRenderTargetTextures=function(P,Y,ie){ae.get(P.texture).__webglTexture=Y,ae.get(P.depthTexture).__webglTexture=ie;const se=ae.get(P);se.__hasExternalTextures=!0,se.__hasExternalTextures&&(se.__autoAllocateDepthBuffer=ie===void 0,se.__autoAllocateDepthBuffer||V.has("WEBGL_multisampled_render_to_texture")===!0&&(console.warn("THREE.WebGLRenderer: Render-to-texture extension was disabled because an external texture was provided"),se.__useRenderToTexture=!1))},this.setRenderTargetFramebuffer=function(P,Y){const ie=ae.get(P);ie.__webglFramebuffer=Y,ie.__useDefaultFramebuffer=Y===void 0},this.setRenderTarget=function(P,Y=0,ie=0){w=P,R=Y,L=ie;let se=!0,ne=null,Me=!1,Ce=!1;if(P){const Be=ae.get(P);Be.__useDefaultFramebuffer!==void 0?(K.bindFramebuffer(E.FRAMEBUFFER,null),se=!1):Be.__webglFramebuffer===void 0?T.setupRenderTarget(P):Be.__hasExternalTextures&&T.rebindTextures(P,ae.get(P.texture).__webglTexture,ae.get(P.depthTexture).__webglTexture);const qe=P.texture;(qe.isData3DTexture||qe.isDataArrayTexture||qe.isCompressedArrayTexture)&&(Ce=!0);const Ve=ae.get(P).__webglFramebuffer;P.isWebGLCubeRenderTarget?(Array.isArray(Ve[Y])?ne=Ve[Y][ie]:ne=Ve[Y],Me=!0):te.isWebGL2&&P.samples>0&&T.useMultisampledRTT(P)===!1?ne=ae.get(P).__webglMultisampledFramebuffer:Array.isArray(Ve)?ne=Ve[ie]:ne=Ve,b.copy(P.viewport),N.copy(P.scissor),A=P.scissorTest}else b.copy(j).multiplyScalar(q).floor(),N.copy(G).multiplyScalar(q).floor(),A=re;if(K.bindFramebuffer(E.FRAMEBUFFER,ne)&&te.drawBuffers&&se&&K.drawBuffers(P,ne),K.viewport(b),K.scissor(N),K.setScissorTest(A),Me){const Be=ae.get(P.texture);E.framebufferTexture2D(E.FRAMEBUFFER,E.COLOR_ATTACHMENT0,E.TEXTURE_CUBE_MAP_POSITIVE_X+Y,Be.__webglTexture,ie)}else if(Ce){const Be=ae.get(P.texture),qe=Y||0;E.framebufferTextureLayer(E.FRAMEBUFFER,E.COLOR_ATTACHMENT0,Be.__webglTexture,ie||0,qe)}B=-1},this.readRenderTargetPixels=function(P,Y,ie,se,ne,Me,Ce){if(!(P&&P.isWebGLRenderTarget)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");return}let Ne=ae.get(P).__webglFramebuffer;if(P.isWebGLCubeRenderTarget&&Ce!==void 0&&(Ne=Ne[Ce]),Ne){K.bindFramebuffer(E.FRAMEBUFFER,Ne);try{const Be=P.texture,qe=Be.format,Ve=Be.type;if(qe!==Xn&&ge.convert(qe)!==E.getParameter(E.IMPLEMENTATION_COLOR_READ_FORMAT)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in RGBA or implementation defined format.");return}const Ge=Ve===So&&(V.has("EXT_color_buffer_half_float")||te.isWebGL2&&V.has("EXT_color_buffer_float"));if(Ve!==es&&ge.convert(Ve)!==E.getParameter(E.IMPLEMENTATION_COLOR_READ_TYPE)&&!(Ve===qi&&(te.isWebGL2||V.has("OES_texture_float")||V.has("WEBGL_color_buffer_float")))&&!Ge){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in UnsignedByteType or implementation defined type.");return}Y>=0&&Y<=P.width-se&&ie>=0&&ie<=P.height-ne&&E.readPixels(Y,ie,se,ne,ge.convert(qe),ge.convert(Ve),Me)}finally{const Be=w!==null?ae.get(w).__webglFramebuffer:null;K.bindFramebuffer(E.FRAMEBUFFER,Be)}}},this.copyFramebufferToTexture=function(P,Y,ie=0){const se=Math.pow(2,-ie),ne=Math.floor(Y.image.width*se),Me=Math.floor(Y.image.height*se);T.setTexture2D(Y,0),E.copyTexSubImage2D(E.TEXTURE_2D,ie,0,0,P.x,P.y,ne,Me),K.unbindTexture()},this.copyTextureToTexture=function(P,Y,ie,se=0){const ne=Y.image.width,Me=Y.image.height,Ce=ge.convert(ie.format),Ne=ge.convert(ie.type);T.setTexture2D(ie,0),E.pixelStorei(E.UNPACK_FLIP_Y_WEBGL,ie.flipY),E.pixelStorei(E.UNPACK_PREMULTIPLY_ALPHA_WEBGL,ie.premultiplyAlpha),E.pixelStorei(E.UNPACK_ALIGNMENT,ie.unpackAlignment),Y.isDataTexture?E.texSubImage2D(E.TEXTURE_2D,se,P.x,P.y,ne,Me,Ce,Ne,Y.image.data):Y.isCompressedTexture?E.compressedTexSubImage2D(E.TEXTURE_2D,se,P.x,P.y,Y.mipmaps[0].width,Y.mipmaps[0].height,Ce,Y.mipmaps[0].data):E.texSubImage2D(E.TEXTURE_2D,se,P.x,P.y,Ce,Ne,Y.image),se===0&&ie.generateMipmaps&&E.generateMipmap(E.TEXTURE_2D),K.unbindTexture()},this.copyTextureToTexture3D=function(P,Y,ie,se,ne=0){if(y.isWebGL1Renderer){console.warn("THREE.WebGLRenderer.copyTextureToTexture3D: can only be used with WebGL2.");return}const Me=P.max.x-P.min.x+1,Ce=P.max.y-P.min.y+1,Ne=P.max.z-P.min.z+1,Be=ge.convert(se.format),qe=ge.convert(se.type);let Ve;if(se.isData3DTexture)T.setTexture3D(se,0),Ve=E.TEXTURE_3D;else if(se.isDataArrayTexture||se.isCompressedArrayTexture)T.setTexture2DArray(se,0),Ve=E.TEXTURE_2D_ARRAY;else{console.warn("THREE.WebGLRenderer.copyTextureToTexture3D: only supports THREE.DataTexture3D and THREE.DataTexture2DArray.");return}E.pixelStorei(E.UNPACK_FLIP_Y_WEBGL,se.flipY),E.pixelStorei(E.UNPACK_PREMULTIPLY_ALPHA_WEBGL,se.premultiplyAlpha),E.pixelStorei(E.UNPACK_ALIGNMENT,se.unpackAlignment);const Ge=E.getParameter(E.UNPACK_ROW_LENGTH),At=E.getParameter(E.UNPACK_IMAGE_HEIGHT),_n=E.getParameter(E.UNPACK_SKIP_PIXELS),It=E.getParameter(E.UNPACK_SKIP_ROWS),ci=E.getParameter(E.UNPACK_SKIP_IMAGES),gt=ie.isCompressedTexture?ie.mipmaps[ne]:ie.image;E.pixelStorei(E.UNPACK_ROW_LENGTH,gt.width),E.pixelStorei(E.UNPACK_IMAGE_HEIGHT,gt.height),E.pixelStorei(E.UNPACK_SKIP_PIXELS,P.min.x),E.pixelStorei(E.UNPACK_SKIP_ROWS,P.min.y),E.pixelStorei(E.UNPACK_SKIP_IMAGES,P.min.z),ie.isDataTexture||ie.isData3DTexture?E.texSubImage3D(Ve,ne,Y.x,Y.y,Y.z,Me,Ce,Ne,Be,qe,gt.data):ie.isCompressedArrayTexture?(console.warn("THREE.WebGLRenderer.copyTextureToTexture3D: untested support for compressed srcTexture."),E.compressedTexSubImage3D(Ve,ne,Y.x,Y.y,Y.z,Me,Ce,Ne,Be,gt.data)):E.texSubImage3D(Ve,ne,Y.x,Y.y,Y.z,Me,Ce,Ne,Be,qe,gt),E.pixelStorei(E.UNPACK_ROW_LENGTH,Ge),E.pixelStorei(E.UNPACK_IMAGE_HEIGHT,At),E.pixelStorei(E.UNPACK_SKIP_PIXELS,_n),E.pixelStorei(E.UNPACK_SKIP_ROWS,It),E.pixelStorei(E.UNPACK_SKIP_IMAGES,ci),ne===0&&se.generateMipmaps&&E.generateMipmap(Ve),K.unbindTexture()},this.initTexture=function(P){P.isCubeTexture?T.setTextureCube(P,0):P.isData3DTexture?T.setTexture3D(P,0):P.isDataArrayTexture||P.isCompressedArrayTexture?T.setTexture2DArray(P,0):T.setTexture2D(P,0),K.unbindTexture()},this.resetState=function(){R=0,L=0,w=null,K.reset(),D.reset()},typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}get coordinateSystem(){return Ri}get outputColorSpace(){return this._outputColorSpace}set outputColorSpace(e){this._outputColorSpace=e;const t=this.getContext();t.drawingBufferColorSpace=e===Au?"display-p3":"srgb",t.unpackColorSpace=at.workingColorSpace===ml?"display-p3":"srgb"}get outputEncoding(){return console.warn("THREE.WebGLRenderer: Property .outputEncoding has been removed. Use .outputColorSpace instead."),this.outputColorSpace===kt?Us:jp}set outputEncoding(e){console.warn("THREE.WebGLRenderer: Property .outputEncoding has been removed. Use .outputColorSpace instead."),this.outputColorSpace=e===Us?kt:Di}get useLegacyLights(){return console.warn("THREE.WebGLRenderer: The property .useLegacyLights has been deprecated. Migrate your lighting according to the following guide: https://discourse.threejs.org/t/updates-to-lighting-in-three-js-r155/53733."),this._useLegacyLights}set useLegacyLights(e){console.warn("THREE.WebGLRenderer: The property .useLegacyLights has been deprecated. Migrate your lighting according to the following guide: https://discourse.threejs.org/t/updates-to-lighting-in-three-js-r155/53733."),this._useLegacyLights=e}}class nb extends _m{}nb.prototype.isWebGL1Renderer=!0;class Lu{constructor(e,t=1,n=1e3){this.isFog=!0,this.name="",this.color=new Qe(e),this.near=t,this.far=n}clone(){return new Lu(this.color,this.near,this.far)}toJSON(){return{type:"Fog",name:this.name,color:this.color.getHex(),near:this.near,far:this.far}}}class ib extends Vt{constructor(){super(),this.isScene=!0,this.type="Scene",this.background=null,this.environment=null,this.fog=null,this.backgroundBlurriness=0,this.backgroundIntensity=1,this.overrideMaterial=null,typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}copy(e,t){return super.copy(e,t),e.background!==null&&(this.background=e.background.clone()),e.environment!==null&&(this.environment=e.environment.clone()),e.fog!==null&&(this.fog=e.fog.clone()),this.backgroundBlurriness=e.backgroundBlurriness,this.backgroundIntensity=e.backgroundIntensity,e.overrideMaterial!==null&&(this.overrideMaterial=e.overrideMaterial.clone()),this.matrixAutoUpdate=e.matrixAutoUpdate,this}toJSON(e){const t=super.toJSON(e);return this.fog!==null&&(t.object.fog=this.fog.toJSON()),this.backgroundBlurriness>0&&(t.object.backgroundBlurriness=this.backgroundBlurriness),this.backgroundIntensity!==1&&(t.object.backgroundIntensity=this.backgroundIntensity),t}}class _i extends Bn{constructor(e,t,n,s=1){super(e,t,n),this.isInstancedBufferAttribute=!0,this.meshPerAttribute=s}copy(e){return super.copy(e),this.meshPerAttribute=e.meshPerAttribute,this}toJSON(){const e=super.toJSON();return e.meshPerAttribute=this.meshPerAttribute,e.isInstancedBufferAttribute=!0,e}}class sb extends No{constructor(e){super(),this.isPointsMaterial=!0,this.type="PointsMaterial",this.color=new Qe(16777215),this.map=null,this.alphaMap=null,this.size=1,this.sizeAttenuation=!0,this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.color.copy(e.color),this.map=e.map,this.alphaMap=e.alphaMap,this.size=e.size,this.sizeAttenuation=e.sizeAttenuation,this.fog=e.fog,this}}const nd=new Lt,Xc=new gl,ma=new _l,_a=new $;class rb extends Vt{constructor(e=new Ni,t=new sb){super(),this.isPoints=!0,this.type="Points",this.geometry=e,this.material=t,this.updateMorphTargets()}copy(e,t){return super.copy(e,t),this.material=Array.isArray(e.material)?e.material.slice():e.material,this.geometry=e.geometry,this}raycast(e,t){const n=this.geometry,s=this.matrixWorld,r=e.params.Points.threshold,o=n.drawRange;if(n.boundingSphere===null&&n.computeBoundingSphere(),ma.copy(n.boundingSphere),ma.applyMatrix4(s),ma.radius+=r,e.ray.intersectsSphere(ma)===!1)return;nd.copy(s).invert(),Xc.copy(e.ray).applyMatrix4(nd);const a=r/((this.scale.x+this.scale.y+this.scale.z)/3),l=a*a,c=n.index,f=n.attributes.position;if(c!==null){const h=Math.max(0,o.start),d=Math.min(c.count,o.start+o.count);for(let g=h,_=d;g<_;g++){const m=c.getX(g);_a.fromBufferAttribute(f,m),id(_a,m,l,s,e,t,this)}}else{const h=Math.max(0,o.start),d=Math.min(f.count,o.start+o.count);for(let g=h,_=d;g<_;g++)_a.fromBufferAttribute(f,g),id(_a,g,l,s,e,t,this)}}updateMorphTargets(){const t=this.geometry.morphAttributes,n=Object.keys(t);if(n.length>0){const s=t[n[0]];if(s!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let r=0,o=s.length;r<o;r++){const a=s[r].name||String(r);this.morphTargetInfluences.push(0),this.morphTargetDictionary[a]=r}}}}}function id(i,e,t,n,s,r,o){const a=Xc.distanceSqToPoint(i);if(a<t){const l=new $;Xc.closestPointToPoint(i,l),l.applyMatrix4(n);const c=s.ray.origin.distanceTo(l);if(c<s.near||c>s.far)return;r.push({distance:c,distanceToRay:Math.sqrt(a),point:l,index:e,face:null,object:o})}}class gm extends Vt{constructor(e,t=1){super(),this.isLight=!0,this.type="Light",this.color=new Qe(e),this.intensity=t}dispose(){}copy(e,t){return super.copy(e,t),this.color.copy(e.color),this.intensity=e.intensity,this}toJSON(e){const t=super.toJSON(e);return t.object.color=this.color.getHex(),t.object.intensity=this.intensity,this.groundColor!==void 0&&(t.object.groundColor=this.groundColor.getHex()),this.distance!==void 0&&(t.object.distance=this.distance),this.angle!==void 0&&(t.object.angle=this.angle),this.decay!==void 0&&(t.object.decay=this.decay),this.penumbra!==void 0&&(t.object.penumbra=this.penumbra),this.shadow!==void 0&&(t.object.shadow=this.shadow.toJSON()),t}}const dc=new Lt,sd=new $,rd=new $;class ob{constructor(e){this.camera=e,this.bias=0,this.normalBias=0,this.radius=1,this.blurSamples=8,this.mapSize=new He(512,512),this.map=null,this.mapPass=null,this.matrix=new Lt,this.autoUpdate=!0,this.needsUpdate=!1,this._frustum=new Ru,this._frameExtents=new He(1,1),this._viewportCount=1,this._viewports=[new Ft(0,0,1,1)]}getViewportCount(){return this._viewportCount}getFrustum(){return this._frustum}updateMatrices(e){const t=this.camera,n=this.matrix;sd.setFromMatrixPosition(e.matrixWorld),t.position.copy(sd),rd.setFromMatrixPosition(e.target.matrixWorld),t.lookAt(rd),t.updateMatrixWorld(),dc.multiplyMatrices(t.projectionMatrix,t.matrixWorldInverse),this._frustum.setFromProjectionMatrix(dc),n.set(.5,0,0,.5,0,.5,0,.5,0,0,.5,.5,0,0,0,1),n.multiply(dc)}getViewport(e){return this._viewports[e]}getFrameExtents(){return this._frameExtents}dispose(){this.map&&this.map.dispose(),this.mapPass&&this.mapPass.dispose()}copy(e){return this.camera=e.camera.clone(),this.bias=e.bias,this.radius=e.radius,this.mapSize.copy(e.mapSize),this}clone(){return new this.constructor().copy(this)}toJSON(){const e={};return this.bias!==0&&(e.bias=this.bias),this.normalBias!==0&&(e.normalBias=this.normalBias),this.radius!==1&&(e.radius=this.radius),(this.mapSize.x!==512||this.mapSize.y!==512)&&(e.mapSize=this.mapSize.toArray()),e.camera=this.camera.toJSON(!1).object,delete e.camera.matrix,e}}class ab extends ob{constructor(){super(new cm(-5,5,5,-5,.5,500)),this.isDirectionalLightShadow=!0}}class lb extends gm{constructor(e,t){super(e,t),this.isDirectionalLight=!0,this.type="DirectionalLight",this.position.copy(Vt.DEFAULT_UP),this.updateMatrix(),this.target=new Vt,this.shadow=new ab}dispose(){this.shadow.dispose()}copy(e){return super.copy(e),this.target=e.target.clone(),this.shadow=e.shadow.clone(),this}}class cb extends gm{constructor(e,t){super(e,t),this.isAmbientLight=!0,this.type="AmbientLight"}}class ub extends Ni{constructor(){super(),this.isInstancedBufferGeometry=!0,this.type="InstancedBufferGeometry",this.instanceCount=1/0}copy(e){return super.copy(e),this.instanceCount=e.instanceCount,this}toJSON(){const e=super.toJSON();return e.instanceCount=this.instanceCount,e.isInstancedBufferGeometry=!0,e}}class fb{constructor(e=!0){this.autoStart=e,this.startTime=0,this.oldTime=0,this.elapsedTime=0,this.running=!1}start(){this.startTime=od(),this.oldTime=this.startTime,this.elapsedTime=0,this.running=!0}stop(){this.getElapsedTime(),this.running=!1,this.autoStart=!1}getElapsedTime(){return this.getDelta(),this.elapsedTime}getDelta(){let e=0;if(this.autoStart&&!this.running)return this.start(),0;if(this.running){const t=od();e=(t-this.oldTime)/1e3,this.oldTime=t,this.elapsedTime+=e}return e}}function od(){return(typeof performance>"u"?Date:performance).now()}class hb{constructor(e,t,n=0,s=1/0){this.ray=new gl(e,t),this.near=n,this.far=s,this.camera=null,this.layers=new wu,this.params={Mesh:{},Line:{threshold:1},LOD:{},Points:{threshold:1},Sprite:{}}}set(e,t){this.ray.set(e,t)}setFromCamera(e,t){t.isPerspectiveCamera?(this.ray.origin.setFromMatrixPosition(t.matrixWorld),this.ray.direction.set(e.x,e.y,.5).unproject(t).sub(this.ray.origin).normalize(),this.camera=t):t.isOrthographicCamera?(this.ray.origin.set(e.x,e.y,(t.near+t.far)/(t.near-t.far)).unproject(t),this.ray.direction.set(0,0,-1).transformDirection(t.matrixWorld),this.camera=t):console.error("THREE.Raycaster: Unsupported camera type: "+t.type)}intersectObject(e,t=!0,n=[]){return qc(e,this,n,t),n.sort(ad),n}intersectObjects(e,t=!0,n=[]){for(let s=0,r=e.length;s<r;s++)qc(e[s],this,n,t);return n.sort(ad),n}}function ad(i,e){return i.distance-e.distance}function qc(i,e,t,n){if(i.layers.test(e.layers)&&i.raycast(e,t),n===!0){const s=i.children;for(let r=0,o=s.length;r<o;r++)qc(s[r],e,t,!0)}}class ld{constructor(e=1,t=0,n=0){return this.radius=e,this.phi=t,this.theta=n,this}set(e,t,n){return this.radius=e,this.phi=t,this.theta=n,this}copy(e){return this.radius=e.radius,this.phi=e.phi,this.theta=e.theta,this}makeSafe(){return this.phi=Math.max(1e-6,Math.min(Math.PI-1e-6,this.phi)),this}setFromVector3(e){return this.setFromCartesianCoords(e.x,e.y,e.z)}setFromCartesianCoords(e,t,n){return this.radius=Math.sqrt(e*e+t*t+n*n),this.radius===0?(this.theta=0,this.phi=0):(this.theta=Math.atan2(e,n),this.phi=Math.acos(sn(t/this.radius,-1,1))),this}clone(){return new this.constructor().copy(this)}}typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("register",{detail:{revision:bu}}));typeof window<"u"&&(window.__THREE__?console.warn("WARNING: Multiple instances of Three.js being imported."):window.__THREE__=bu);const cd={type:"change"},pc={type:"start"},ud={type:"end"},ga=new gl,fd=new Si,db=Math.cos(70*Kv.DEG2RAD);class pb extends Hs{constructor(e,t){super(),this.object=e,this.domElement=t,this.domElement.style.touchAction="none",this.enabled=!0,this.target=new $,this.cursor=new $,this.minDistance=0,this.maxDistance=1/0,this.minZoom=0,this.maxZoom=1/0,this.minTargetRadius=0,this.maxTargetRadius=1/0,this.minPolarAngle=0,this.maxPolarAngle=Math.PI,this.minAzimuthAngle=-1/0,this.maxAzimuthAngle=1/0,this.enableDamping=!1,this.dampingFactor=.05,this.enableZoom=!0,this.zoomSpeed=1,this.enableRotate=!0,this.rotateSpeed=1,this.enablePan=!0,this.panSpeed=1,this.screenSpacePanning=!0,this.keyPanSpeed=7,this.zoomToCursor=!1,this.autoRotate=!1,this.autoRotateSpeed=2,this.keys={LEFT:"ArrowLeft",UP:"ArrowUp",RIGHT:"ArrowRight",BOTTOM:"ArrowDown"},this.mouseButtons={LEFT:Xs.ROTATE,MIDDLE:Xs.DOLLY,RIGHT:Xs.PAN},this.touches={ONE:qs.ROTATE,TWO:qs.DOLLY_PAN},this.target0=this.target.clone(),this.position0=this.object.position.clone(),this.zoom0=this.object.zoom,this._domElementKeyEvents=null,this.getPolarAngle=function(){return a.phi},this.getAzimuthalAngle=function(){return a.theta},this.getDistance=function(){return this.object.position.distanceTo(this.target)},this.listenToKeyEvents=function(D){D.addEventListener("keydown",xe),this._domElementKeyEvents=D},this.stopListenToKeyEvents=function(){this._domElementKeyEvents.removeEventListener("keydown",xe),this._domElementKeyEvents=null},this.saveState=function(){n.target0.copy(n.target),n.position0.copy(n.object.position),n.zoom0=n.object.zoom},this.reset=function(){n.target.copy(n.target0),n.object.position.copy(n.position0),n.object.zoom=n.zoom0,n.object.updateProjectionMatrix(),n.dispatchEvent(cd),n.update(),r=s.NONE},this.update=function(){const D=new $,pe=new ks().setFromUnitVectors(e.up,new $(0,1,0)),we=pe.clone().invert(),Ee=new $,he=new ks,F=new $,me=2*Math.PI;return function(Oe=null){const Pe=n.object.position;D.copy(Pe).sub(n.target),D.applyQuaternion(pe),a.setFromVector3(D),n.autoRotate&&r===s.NONE&&A(b(Oe)),n.enableDamping?(a.theta+=l.theta*n.dampingFactor,a.phi+=l.phi*n.dampingFactor):(a.theta+=l.theta,a.phi+=l.phi);let Ze=n.minAzimuthAngle,Je=n.maxAzimuthAngle;isFinite(Ze)&&isFinite(Je)&&(Ze<-Math.PI?Ze+=me:Ze>Math.PI&&(Ze-=me),Je<-Math.PI?Je+=me:Je>Math.PI&&(Je-=me),Ze<=Je?a.theta=Math.max(Ze,Math.min(Je,a.theta)):a.theta=a.theta>(Ze+Je)/2?Math.max(Ze,a.theta):Math.min(Je,a.theta)),a.phi=Math.max(n.minPolarAngle,Math.min(n.maxPolarAngle,a.phi)),a.makeSafe(),n.enableDamping===!0?n.target.addScaledVector(u,n.dampingFactor):n.target.add(u),n.target.sub(n.cursor),n.target.clampLength(n.minTargetRadius,n.maxTargetRadius),n.target.add(n.cursor),n.zoomToCursor&&L||n.object.isOrthographicCamera?a.radius=j(a.radius):a.radius=j(a.radius*c),D.setFromSpherical(a),D.applyQuaternion(we),Pe.copy(n.target).add(D),n.object.lookAt(n.target),n.enableDamping===!0?(l.theta*=1-n.dampingFactor,l.phi*=1-n.dampingFactor,u.multiplyScalar(1-n.dampingFactor)):(l.set(0,0,0),u.set(0,0,0));let St=!1;if(n.zoomToCursor&&L){let Tt=null;if(n.object.isPerspectiveCamera){const nt=D.length();Tt=j(nt*c);const Rt=nt-Tt;n.object.position.addScaledVector(S,Rt),n.object.updateMatrixWorld()}else if(n.object.isOrthographicCamera){const nt=new $(R.x,R.y,0);nt.unproject(n.object),n.object.zoom=Math.max(n.minZoom,Math.min(n.maxZoom,n.object.zoom/c)),n.object.updateProjectionMatrix(),St=!0;const Rt=new $(R.x,R.y,0);Rt.unproject(n.object),n.object.position.sub(Rt).add(nt),n.object.updateMatrixWorld(),Tt=D.length()}else console.warn("WARNING: OrbitControls.js encountered an unknown camera type - zoom to cursor disabled."),n.zoomToCursor=!1;Tt!==null&&(this.screenSpacePanning?n.target.set(0,0,-1).transformDirection(n.object.matrix).multiplyScalar(Tt).add(n.object.position):(ga.origin.copy(n.object.position),ga.direction.set(0,0,-1).transformDirection(n.object.matrix),Math.abs(n.object.up.dot(ga.direction))<db?e.lookAt(n.target):(fd.setFromNormalAndCoplanarPoint(n.object.up,n.target),ga.intersectPlane(fd,n.target))))}else n.object.isOrthographicCamera&&(n.object.zoom=Math.max(n.minZoom,Math.min(n.maxZoom,n.object.zoom/c)),n.object.updateProjectionMatrix(),St=!0);return c=1,L=!1,St||Ee.distanceToSquared(n.object.position)>o||8*(1-he.dot(n.object.quaternion))>o||F.distanceToSquared(n.target)>0?(n.dispatchEvent(cd),Ee.copy(n.object.position),he.copy(n.object.quaternion),F.copy(n.target),!0):!1}}(),this.dispose=function(){n.domElement.removeEventListener("contextmenu",ke),n.domElement.removeEventListener("pointerdown",T),n.domElement.removeEventListener("pointercancel",U),n.domElement.removeEventListener("wheel",J),n.domElement.removeEventListener("pointermove",M),n.domElement.removeEventListener("pointerup",U),n._domElementKeyEvents!==null&&(n._domElementKeyEvents.removeEventListener("keydown",xe),n._domElementKeyEvents=null)};const n=this,s={NONE:-1,ROTATE:0,DOLLY:1,PAN:2,TOUCH_ROTATE:3,TOUCH_PAN:4,TOUCH_DOLLY_PAN:5,TOUCH_DOLLY_ROTATE:6};let r=s.NONE;const o=1e-6,a=new ld,l=new ld;let c=1;const u=new $,f=new He,h=new He,d=new He,g=new He,_=new He,m=new He,p=new He,x=new He,y=new He,S=new $,R=new He;let L=!1;const w=[],B={};let v=!1;function b(D){return D!==null?2*Math.PI/60*n.autoRotateSpeed*D:2*Math.PI/60/60*n.autoRotateSpeed}function N(D){const pe=Math.abs(D*.01);return Math.pow(.95,n.zoomSpeed*pe)}function A(D){l.theta-=D}function I(D){l.phi-=D}const O=function(){const D=new $;return function(we,Ee){D.setFromMatrixColumn(Ee,0),D.multiplyScalar(-we),u.add(D)}}(),k=function(){const D=new $;return function(we,Ee){n.screenSpacePanning===!0?D.setFromMatrixColumn(Ee,1):(D.setFromMatrixColumn(Ee,0),D.crossVectors(n.object.up,D)),D.multiplyScalar(we),u.add(D)}}(),H=function(){const D=new $;return function(we,Ee){const he=n.domElement;if(n.object.isPerspectiveCamera){const F=n.object.position;D.copy(F).sub(n.target);let me=D.length();me*=Math.tan(n.object.fov/2*Math.PI/180),O(2*we*me/he.clientHeight,n.object.matrix),k(2*Ee*me/he.clientHeight,n.object.matrix)}else n.object.isOrthographicCamera?(O(we*(n.object.right-n.object.left)/n.object.zoom/he.clientWidth,n.object.matrix),k(Ee*(n.object.top-n.object.bottom)/n.object.zoom/he.clientHeight,n.object.matrix)):(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - pan disabled."),n.enablePan=!1)}}();function q(D){n.object.isPerspectiveCamera||n.object.isOrthographicCamera?c/=D:(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - dolly/zoom disabled."),n.enableZoom=!1)}function Z(D){n.object.isPerspectiveCamera||n.object.isOrthographicCamera?c*=D:(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - dolly/zoom disabled."),n.enableZoom=!1)}function W(D,pe){if(!n.zoomToCursor)return;L=!0;const we=n.domElement.getBoundingClientRect(),Ee=D-we.left,he=pe-we.top,F=we.width,me=we.height;R.x=Ee/F*2-1,R.y=-(he/me)*2+1,S.set(R.x,R.y,1).unproject(n.object).sub(n.object.position).normalize()}function j(D){return Math.max(n.minDistance,Math.min(n.maxDistance,D))}function G(D){f.set(D.clientX,D.clientY)}function re(D){W(D.clientX,D.clientX),p.set(D.clientX,D.clientY)}function Q(D){g.set(D.clientX,D.clientY)}function le(D){h.set(D.clientX,D.clientY),d.subVectors(h,f).multiplyScalar(n.rotateSpeed);const pe=n.domElement;A(2*Math.PI*d.x/pe.clientHeight),I(2*Math.PI*d.y/pe.clientHeight),f.copy(h),n.update()}function _e(D){x.set(D.clientX,D.clientY),y.subVectors(x,p),y.y>0?q(N(y.y)):y.y<0&&Z(N(y.y)),p.copy(x),n.update()}function be(D){_.set(D.clientX,D.clientY),m.subVectors(_,g).multiplyScalar(n.panSpeed),H(m.x,m.y),g.copy(_),n.update()}function Te(D){W(D.clientX,D.clientY),D.deltaY<0?Z(N(D.deltaY)):D.deltaY>0&&q(N(D.deltaY)),n.update()}function Ue(D){let pe=!1;switch(D.code){case n.keys.UP:D.ctrlKey||D.metaKey||D.shiftKey?I(2*Math.PI*n.rotateSpeed/n.domElement.clientHeight):H(0,n.keyPanSpeed),pe=!0;break;case n.keys.BOTTOM:D.ctrlKey||D.metaKey||D.shiftKey?I(-2*Math.PI*n.rotateSpeed/n.domElement.clientHeight):H(0,-n.keyPanSpeed),pe=!0;break;case n.keys.LEFT:D.ctrlKey||D.metaKey||D.shiftKey?A(2*Math.PI*n.rotateSpeed/n.domElement.clientHeight):H(n.keyPanSpeed,0),pe=!0;break;case n.keys.RIGHT:D.ctrlKey||D.metaKey||D.shiftKey?A(-2*Math.PI*n.rotateSpeed/n.domElement.clientHeight):H(-n.keyPanSpeed,0),pe=!0;break}pe&&(D.preventDefault(),n.update())}function Ie(D){if(w.length===1)f.set(D.pageX,D.pageY);else{const pe=ge(D),we=.5*(D.pageX+pe.x),Ee=.5*(D.pageY+pe.y);f.set(we,Ee)}}function Se(D){if(w.length===1)g.set(D.pageX,D.pageY);else{const pe=ge(D),we=.5*(D.pageX+pe.x),Ee=.5*(D.pageY+pe.y);g.set(we,Ee)}}function Ke(D){const pe=ge(D),we=D.pageX-pe.x,Ee=D.pageY-pe.y,he=Math.sqrt(we*we+Ee*Ee);p.set(0,he)}function E(D){n.enableZoom&&Ke(D),n.enablePan&&Se(D)}function z(D){n.enableZoom&&Ke(D),n.enableRotate&&Ie(D)}function V(D){if(w.length==1)h.set(D.pageX,D.pageY);else{const we=ge(D),Ee=.5*(D.pageX+we.x),he=.5*(D.pageY+we.y);h.set(Ee,he)}d.subVectors(h,f).multiplyScalar(n.rotateSpeed);const pe=n.domElement;A(2*Math.PI*d.x/pe.clientHeight),I(2*Math.PI*d.y/pe.clientHeight),f.copy(h)}function te(D){if(w.length===1)_.set(D.pageX,D.pageY);else{const pe=ge(D),we=.5*(D.pageX+pe.x),Ee=.5*(D.pageY+pe.y);_.set(we,Ee)}m.subVectors(_,g).multiplyScalar(n.panSpeed),H(m.x,m.y),g.copy(_)}function K(D){const pe=ge(D),we=D.pageX-pe.x,Ee=D.pageY-pe.y,he=Math.sqrt(we*we+Ee*Ee);x.set(0,he),y.set(0,Math.pow(x.y/p.y,n.zoomSpeed)),q(y.y),p.copy(x);const F=(D.pageX+pe.x)*.5,me=(D.pageY+pe.y)*.5;W(F,me)}function oe(D){n.enableZoom&&K(D),n.enablePan&&te(D)}function ae(D){n.enableZoom&&K(D),n.enableRotate&&V(D)}function T(D){n.enabled!==!1&&(w.length===0&&(n.domElement.setPointerCapture(D.pointerId),n.domElement.addEventListener("pointermove",M),n.domElement.addEventListener("pointerup",U)),De(D),D.pointerType==="touch"?Ae(D):ee(D))}function M(D){n.enabled!==!1&&(D.pointerType==="touch"?ce(D):X(D))}function U(D){Le(D),w.length===0&&(n.domElement.releasePointerCapture(D.pointerId),n.domElement.removeEventListener("pointermove",M),n.domElement.removeEventListener("pointerup",U)),n.dispatchEvent(ud),r=s.NONE}function ee(D){let pe;switch(D.button){case 0:pe=n.mouseButtons.LEFT;break;case 1:pe=n.mouseButtons.MIDDLE;break;case 2:pe=n.mouseButtons.RIGHT;break;default:pe=-1}switch(pe){case Xs.DOLLY:if(n.enableZoom===!1)return;re(D),r=s.DOLLY;break;case Xs.ROTATE:if(D.ctrlKey||D.metaKey||D.shiftKey){if(n.enablePan===!1)return;Q(D),r=s.PAN}else{if(n.enableRotate===!1)return;G(D),r=s.ROTATE}break;case Xs.PAN:if(D.ctrlKey||D.metaKey||D.shiftKey){if(n.enableRotate===!1)return;G(D),r=s.ROTATE}else{if(n.enablePan===!1)return;Q(D),r=s.PAN}break;default:r=s.NONE}r!==s.NONE&&n.dispatchEvent(pc)}function X(D){switch(r){case s.ROTATE:if(n.enableRotate===!1)return;le(D);break;case s.DOLLY:if(n.enableZoom===!1)return;_e(D);break;case s.PAN:if(n.enablePan===!1)return;be(D);break}}function J(D){n.enabled===!1||n.enableZoom===!1||r!==s.NONE||(D.preventDefault(),n.dispatchEvent(pc),Te(fe(D)),n.dispatchEvent(ud))}function fe(D){const pe=D.deltaMode,we={clientX:D.clientX,clientY:D.clientY,deltaY:D.deltaY};switch(pe){case 1:we.deltaY*=16;break;case 2:we.deltaY*=100;break}return D.ctrlKey&&!v&&(we.deltaY*=10),we}function ue(D){D.key==="Control"&&(v=!0,document.addEventListener("keyup",de,{passive:!0,capture:!0}))}function de(D){D.key==="Control"&&(v=!1,document.removeEventListener("keyup",de,{passive:!0,capture:!0}))}function xe(D){n.enabled===!1||n.enablePan===!1||Ue(D)}function Ae(D){switch(Re(D),w.length){case 1:switch(n.touches.ONE){case qs.ROTATE:if(n.enableRotate===!1)return;Ie(D),r=s.TOUCH_ROTATE;break;case qs.PAN:if(n.enablePan===!1)return;Se(D),r=s.TOUCH_PAN;break;default:r=s.NONE}break;case 2:switch(n.touches.TWO){case qs.DOLLY_PAN:if(n.enableZoom===!1&&n.enablePan===!1)return;E(D),r=s.TOUCH_DOLLY_PAN;break;case qs.DOLLY_ROTATE:if(n.enableZoom===!1&&n.enableRotate===!1)return;z(D),r=s.TOUCH_DOLLY_ROTATE;break;default:r=s.NONE}break;default:r=s.NONE}r!==s.NONE&&n.dispatchEvent(pc)}function ce(D){switch(Re(D),r){case s.TOUCH_ROTATE:if(n.enableRotate===!1)return;V(D),n.update();break;case s.TOUCH_PAN:if(n.enablePan===!1)return;te(D),n.update();break;case s.TOUCH_DOLLY_PAN:if(n.enableZoom===!1&&n.enablePan===!1)return;oe(D),n.update();break;case s.TOUCH_DOLLY_ROTATE:if(n.enableZoom===!1&&n.enableRotate===!1)return;ae(D),n.update();break;default:r=s.NONE}}function ke(D){n.enabled!==!1&&D.preventDefault()}function De(D){w.push(D.pointerId)}function Le(D){delete B[D.pointerId];for(let pe=0;pe<w.length;pe++)if(w[pe]==D.pointerId){w.splice(pe,1);return}}function Re(D){let pe=B[D.pointerId];pe===void 0&&(pe=new He,B[D.pointerId]=pe),pe.set(D.pageX,D.pageY)}function ge(D){const pe=D.pointerId===w[0]?w[1]:w[0];return B[pe]}n.domElement.addEventListener("contextmenu",ke),n.domElement.addEventListener("pointerdown",T),n.domElement.addEventListener("pointercancel",U),n.domElement.addEventListener("wheel",J,{passive:!1}),document.addEventListener("keydown",ue,{passive:!0,capture:!0}),this.update()}}const mb=`
  precision highp float;

  attribute vec3 instancePosition;
  attribute vec3 instanceVelocity;
  attribute float instanceLife;
  attribute float instanceMaxLife;
  attribute float instanceSize;
  attribute vec3 instanceColor;
  attribute float instanceRotation;
  attribute float instanceRotationSpeed;
  attribute float instanceActive;

  uniform float uTime;
  uniform float uDeltaTime;
  uniform vec3 uGravity;
  uniform float uPixelRatio;

  varying float vLife;
  varying float vMaxLife;
  varying vec3 vColor;
  varying float vRotation;
  varying float vActive;

  void main() {
    vLife = instanceLife;
    vMaxLife = instanceMaxLife;
    vColor = instanceColor;
    vRotation = instanceRotation;
    vActive = instanceActive;

    if (instanceActive < 0.5) {
      gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
      gl_PointSize = 0.0;
      return;
    }

    vec3 pos = instancePosition;
    vec3 vel = instanceVelocity;
    float life = instanceLife;
    float rotation = instanceRotation;

    if (life > 0.0) {
      vel += uGravity * uDeltaTime;
      pos += vel * uDeltaTime;
      life -= uDeltaTime;
      rotation += instanceRotationSpeed * uDeltaTime;
    }

    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
    float lifeRatio = life / instanceMaxLife;
    
    gl_PointSize = instanceSize * uPixelRatio * (1.0 - lifeRatio * 0.5) * (300.0 / -mvPosition.z);
    gl_Position = projectionMatrix * mvPosition;
  }
`,_b=`
  precision highp float;

  varying float vLife;
  varying float vMaxLife;
  varying vec3 vColor;
  varying float vRotation;
  varying float vActive;

  void main() {
    if (vActive < 0.5 || vLife <= 0.0) {
      discard;
    }

    vec2 center = gl_PointCoord - vec2(0.5);
    
    float cosR = cos(vRotation);
    float sinR = sin(vRotation);
    vec2 rotated = vec2(
      center.x * cosR - center.y * sinR,
      center.x * sinR + center.y * cosR
    );
    
    float dist = length(rotated);
    float alpha = 1.0 - smoothstep(0.0, 0.5, dist);
    
    float lifeRatio = vLife / vMaxLife;
    alpha *= lifeRatio;
    
    if (alpha < 0.01) discard;
    
    gl_FragColor = vec4(vColor, alpha);
  }
`;class gb{constructor(e,t={}){this.scene=e,this.config={maxParticles:1e6,particleCount:5e4,emissionRate:5e3,speed:{min:1,max:3},life:{min:1,max:3},size:{min:.1,max:.5},color:{start:"#ff6600",end:"#ff0000"},direction:{x:0,y:1,z:0},spread:.5,gravity:{x:0,y:-.5,z:0},emitterPosition:{x:0,y:0,z:0},emitterShape:"point",emitterRadius:1,rotationSpeed:{min:0,max:2},blending:"additive",...t},this.time=0,this.deltaTime=0,this.emissionAccumulator=0,this.paused=!1,this.particleCount=0,this.initGeometry(),this.initMaterial(),this.initPoints(),this.initParticleData()}initGeometry(){const e=this.config.maxParticles;this.geometry=new ub,this.geometry.instanceCount=e;const t=new Float32Array([0,0,0]);this.geometry.setAttribute("position",new Bn(t,3)),this.instancePosition=new Float32Array(e*3),this.instanceVelocity=new Float32Array(e*3),this.instanceLife=new Float32Array(e),this.instanceMaxLife=new Float32Array(e),this.instanceSize=new Float32Array(e),this.instanceColor=new Float32Array(e*3),this.instanceRotation=new Float32Array(e),this.instanceRotationSpeed=new Float32Array(e),this.instanceActive=new Float32Array(e),this.geometry.setAttribute("instancePosition",new _i(this.instancePosition,3)),this.geometry.setAttribute("instanceVelocity",new _i(this.instanceVelocity,3)),this.geometry.setAttribute("instanceLife",new _i(this.instanceLife,1)),this.geometry.setAttribute("instanceMaxLife",new _i(this.instanceMaxLife,1)),this.geometry.setAttribute("instanceSize",new _i(this.instanceSize,1)),this.geometry.setAttribute("instanceColor",new _i(this.instanceColor,3)),this.geometry.setAttribute("instanceRotation",new _i(this.instanceRotation,1)),this.geometry.setAttribute("instanceRotationSpeed",new _i(this.instanceRotationSpeed,1)),this.geometry.setAttribute("instanceActive",new _i(this.instanceActive,1)),this.freeIndices=[];for(let n=e-1;n>=0;n--)this.freeIndices.push(n),this.instanceActive[n]=0;this.activeIndices=[]}initMaterial(){const e=this.config.blending==="additive"?ka:Ji;this.material=new rs({uniforms:{uTime:{value:0},uDeltaTime:{value:0},uGravity:{value:new $},uPixelRatio:{value:Math.min(window.devicePixelRatio,2)}},vertexShader:mb,fragmentShader:_b,transparent:!0,blending:e,depthWrite:!1})}initPoints(){this.points=new rb(this.geometry,this.material),this.points.frustumCulled=!1,this.scene.add(this.points)}initParticleData(){this.particles=new Array(this.config.maxParticles).fill(null).map((e,t)=>({active:!1,index:t}))}emitParticle(){if(this.freeIndices.length===0||this.activeIndices.length>=this.config.particleCount)return;const e=this.freeIndices.pop();this.activeIndices.push(e);const{emitterPosition:t,emitterShape:n,emitterRadius:s,direction:r,spread:o}=this.config;let a=t.x,l=t.y,c=t.z;if(n==="sphere"){const A=Math.random()*Math.PI*2,I=Math.acos(2*Math.random()-1),O=Math.random()*s;a+=O*Math.sin(I)*Math.cos(A),l+=O*Math.sin(I)*Math.sin(A),c+=O*Math.cos(I)}else if(n==="circle"){const A=Math.random()*Math.PI*2,I=Math.random()*s;a+=Math.cos(A)*I,c+=Math.sin(A)*I}else n==="box"&&(a+=(Math.random()-.5)*s*2,l+=(Math.random()-.5)*s*2,c+=(Math.random()-.5)*s*2);const u=r.x+(Math.random()-.5)*o,f=r.y+(Math.random()-.5)*o,h=r.z+(Math.random()-.5)*o,d=Math.sqrt(u*u+f*f+h*h),g=this.randomRange(this.config.speed.min,this.config.speed.max),_=u/d*g,m=f/d*g,p=h/d*g,x=this.randomRange(this.config.life.min,this.config.life.max),y=this.randomRange(this.config.size.min,this.config.size.max),S=new Qe(this.config.color.start),R=new Qe(this.config.color.end),L=Math.random(),w=S.r+(R.r-S.r)*L,B=S.g+(R.g-S.g)*L,v=S.b+(R.b-S.b)*L,b=Math.random()*Math.PI*2,N=this.randomRange(this.config.rotationSpeed.min,this.config.rotationSpeed.max);this.instancePosition[e*3]=a,this.instancePosition[e*3+1]=l,this.instancePosition[e*3+2]=c,this.instanceVelocity[e*3]=_,this.instanceVelocity[e*3+1]=m,this.instanceVelocity[e*3+2]=p,this.instanceLife[e]=x,this.instanceMaxLife[e]=x,this.instanceSize[e]=y,this.instanceColor[e*3]=w,this.instanceColor[e*3+1]=B,this.instanceColor[e*3+2]=v,this.instanceRotation[e]=b,this.instanceRotationSpeed[e]=N,this.instanceActive[e]=1,this.geometry.attributes.instancePosition.needsUpdate=!0,this.geometry.attributes.instanceVelocity.needsUpdate=!0,this.geometry.attributes.instanceLife.needsUpdate=!0,this.geometry.attributes.instanceMaxLife.needsUpdate=!0,this.geometry.attributes.instanceSize.needsUpdate=!0,this.geometry.attributes.instanceColor.needsUpdate=!0,this.geometry.attributes.instanceRotation.needsUpdate=!0,this.geometry.attributes.instanceRotationSpeed.needsUpdate=!0,this.geometry.attributes.instanceActive.needsUpdate=!0}randomRange(e,t){return e+Math.random()*(t-e)}update(e){if(this.paused)return;this.time+=e,this.deltaTime=Math.min(e,.05),this.emissionAccumulator+=this.config.emissionRate*this.deltaTime;const t=Math.floor(this.emissionAccumulator);for(let n=0;n<t;n++)this.emitParticle();this.emissionAccumulator-=t;for(let n=this.activeIndices.length-1;n>=0;n--){const s=this.activeIndices[n];if(this.instanceLife[s]-=this.deltaTime,this.instanceLife[s]<=0){this.instanceActive[s]=0,this.geometry.attributes.instanceActive.needsUpdate=!0,this.geometry.attributes.instanceLife.needsUpdate=!0,this.freeIndices.push(s),this.activeIndices.splice(n,1);continue}this.instanceVelocity[s*3]+=this.config.gravity.x*this.deltaTime,this.instanceVelocity[s*3+1]+=this.config.gravity.y*this.deltaTime,this.instanceVelocity[s*3+2]+=this.config.gravity.z*this.deltaTime,this.instancePosition[s*3]+=this.instanceVelocity[s*3]*this.deltaTime,this.instancePosition[s*3+1]+=this.instanceVelocity[s*3+1]*this.deltaTime,this.instancePosition[s*3+2]+=this.instanceVelocity[s*3+2]*this.deltaTime,this.instanceRotation[s]+=this.instanceRotationSpeed[s]*this.deltaTime}this.activeIndices.length>0&&(this.geometry.attributes.instancePosition.needsUpdate=!0,this.geometry.attributes.instanceVelocity.needsUpdate=!0,this.geometry.attributes.instanceLife.needsUpdate=!0,this.geometry.attributes.instanceRotation.needsUpdate=!0),this.material.uniforms.uTime.value=this.time,this.material.uniforms.uDeltaTime.value=this.deltaTime,this.material.uniforms.uGravity.value.set(this.config.gravity.x,this.config.gravity.y,this.config.gravity.z),this.particleCount=this.activeIndices.length}updateConfig(e){const t=this.config.blending;Object.assign(this.config,e),t!==this.config.blending&&(this.material.blending=this.config.blending==="additive"?ka:Ji,this.material.needsUpdate=!0)}getConfig(){return JSON.parse(JSON.stringify(this.config))}clear(){for(const e of this.activeIndices)this.instanceActive[e]=0,this.freeIndices.push(e);this.activeIndices=[],this.particleCount=0,this.emissionAccumulator=0,this.geometry.attributes.instanceActive.needsUpdate=!0,this.geometry.attributes.instanceLife.needsUpdate=!0}pause(){this.paused=!0}resume(){this.paused=!1}dispose(){this.scene.remove(this.points),this.geometry.dispose(),this.material.dispose()}get particles(){return{length:this.particleCount}}}const Wi={fire:{name:"火焰",icon:"🔥",config:{maxParticles:1e6,particleCount:15e4,emissionRate:3e4,speed:{min:2,max:5},life:{min:.5,max:1.5},size:{min:.2,max:.8},color:{start:"#ffff00",end:"#ff0000"},direction:{x:0,y:1,z:0},spread:.6,gravity:{x:0,y:-1,z:0},emitterPosition:{x:0,y:-2,z:0},emitterShape:"circle",emitterRadius:.5,rotationSpeed:{min:0,max:3},blending:"additive"}},smoke:{name:"烟雾",icon:"💨",config:{maxParticles:5e5,particleCount:8e4,emissionRate:8e3,speed:{min:.5,max:1.5},life:{min:2,max:5},size:{min:.5,max:1.5},color:{start:"#888888",end:"#333333"},direction:{x:0,y:1,z:0},spread:.8,gravity:{x:0,y:.2,z:0},emitterPosition:{x:0,y:-2,z:0},emitterShape:"circle",emitterRadius:.3,rotationSpeed:{min:.5,max:2},blending:"normal"}},stars:{name:"星空",icon:"✨",config:{maxParticles:2e6,particleCount:5e5,emissionRate:5e4,speed:{min:.05,max:.2},life:{min:3,max:8},size:{min:.05,max:.2},color:{start:"#ffffff",end:"#88ccff"},direction:{x:0,y:0,z:0},spread:0,gravity:{x:0,y:0,z:0},emitterPosition:{x:0,y:0,z:0},emitterShape:"sphere",emitterRadius:20,rotationSpeed:{min:0,max:1},blending:"additive"}},snow:{name:"雪花",icon:"❄️",config:{maxParticles:1e6,particleCount:2e5,emissionRate:15e3,speed:{min:.3,max:1},life:{min:5,max:10},size:{min:.1,max:.4},color:{start:"#ffffff",end:"#aaddff"},direction:{x:0,y:-1,z:0},spread:.3,gravity:{x:0,y:-.1,z:0},emitterPosition:{x:0,y:8,z:0},emitterShape:"box",emitterRadius:15,rotationSpeed:{min:1,max:4},blending:"additive"}}};class vb{constructor(e){this.container=e,this.particleEngines=[],this.isPlaying=!0,this.animationId=null,this.clock=new fb,this.initScene(),this.initCamera(),this.initRenderer(),this.initControls(),this.initLights(),this.animate(),window.addEventListener("resize",this.onResize.bind(this))}initScene(){this.scene=new ib,this.scene.background=new Qe(657935),this.scene.fog=new Lu(657935,10,50)}initCamera(){this.camera=new Un(75,this.container.clientWidth/this.container.clientHeight,.1,1e3),this.camera.position.set(0,0,8)}initRenderer(){this.renderer=new _m({antialias:!0,powerPreference:"high-performance"}),this.renderer.setSize(this.container.clientWidth,this.container.clientHeight),this.renderer.setPixelRatio(Math.min(window.devicePixelRatio,2)),this.container.appendChild(this.renderer.domElement)}initControls(){this.controls=new pb(this.camera,this.renderer.domElement),this.controls.enableDamping=!0,this.controls.dampingFactor=.05,this.controls.minDistance=2,this.controls.maxDistance=50}initLights(){const e=new cb(16777215,.5);this.scene.add(e);const t=new lb(16777215,1);t.position.set(5,10,7),this.scene.add(t)}addParticleSystem(e="fire",t={}){const s={...(Wi[e]||Wi.fire).config,...t},r=new gb(this.scene,s);return this.particleEngines.push(r),r}removeParticleSystem(e){const t=this.particleEngines.indexOf(e);t>-1&&(e.dispose(),this.particleEngines.splice(t,1))}clearAllParticleSystems(){for(const e of this.particleEngines)e.dispose();this.particleEngines=[]}updateParticleSystem(e,t){e&&e.updateConfig(t)}animate(){this.animationId=requestAnimationFrame(this.animate.bind(this));const e=Math.min(this.clock.getDelta(),.1);if(this.isPlaying)for(const t of this.particleEngines)t.update(e);this.controls.update(),this.renderer.render(this.scene,this.camera)}play(){this.isPlaying=!0;for(const e of this.particleEngines)e.resume()}pause(){this.isPlaying=!1;for(const e of this.particleEngines)e.pause()}reset(){for(const e of this.particleEngines)e.clear()}setBackgroundColor(e){this.scene.background=new Qe(e),this.scene.fog&&(this.scene.fog.color=new Qe(e))}onResize(){this.camera.aspect=this.container.clientWidth/this.container.clientHeight,this.camera.updateProjectionMatrix(),this.renderer.setSize(this.container.clientWidth,this.container.clientHeight)}dispose(){this.animationId&&cancelAnimationFrame(this.animationId),window.removeEventListener("resize",this.onResize.bind(this)),this.clearAllParticleSystems(),this.controls.dispose(),this.renderer.dispose(),this.container.removeChild(this.renderer.domElement)}}function xi(i){if(i===void 0)throw new ReferenceError("this hasn't been initialised - super() hasn't been called");return i}function vm(i,e){i.prototype=Object.create(e.prototype),i.prototype.constructor=i,i.__proto__=e}/*!
 * GSAP 3.15.0
 * https://gsap.com
 *
 * @license Copyright 2008-2026, GreenSock. All rights reserved.
 * Subject to the terms at https://gsap.com/standard-license
 * @author: Jack Doyle, jack@greensock.com
*/var An={autoSleep:120,force3D:"auto",nullTargetWarn:1,units:{lineHeight:""}},Mo={duration:.5,overwrite:!1,delay:0},Du,Ht,_t,Nn=1e8,ft=1/Nn,Yc=Math.PI*2,xb=Yc/4,yb=0,xm=Math.sqrt,Sb=Math.cos,Mb=Math.sin,zt=function(e){return typeof e=="string"},Et=function(e){return typeof e=="function"},Ui=function(e){return typeof e=="number"},Uu=function(e){return typeof e>"u"},li=function(e){return typeof e=="object"},fn=function(e){return e!==!1},Iu=function(){return typeof window<"u"},va=function(e){return Et(e)||zt(e)},ym=typeof ArrayBuffer=="function"&&ArrayBuffer.isView||function(){},jt=Array.isArray,Eb=/random\([^)]+\)/g,bb=/,\s*/g,hd=/(?:-?\.?\d|\.)+/gi,Sm=/[-+=.]*\d+[.e\-+]*\d*[e\-+]*\d*/g,dr=/[-+=.]*\d+[.e-]*\d*[a-z%]*/g,mc=/[-+=.]*\d+\.?\d*(?:e-|e\+)?\d*/gi,Mm=/[+-]=-?[.\d]+/,Tb=/[^,'"\[\]\s]+/gi,Ab=/^[+\-=e\s\d]*\d+[.\d]*([a-z]*|%)\s*$/i,xt,Jn,$c,Ou,wn={},Ya={},Em,bm=function(e){return(Ya=Dr(e,wn))&&mn},Nu=function(e,t){return console.warn("Invalid property",e,"set to",t,"Missing plugin? gsap.registerPlugin()")},Eo=function(e,t){return!t&&console.warn(e)},Tm=function(e,t){return e&&(wn[e]=t)&&Ya&&(Ya[e]=t)||wn},bo=function(){return 0},wb={suppressEvents:!0,isStart:!0,kill:!1},Ra={suppressEvents:!0,kill:!1},Rb={suppressEvents:!0},Fu={},ts=[],jc={},Am,xn={},_c={},dd=30,Ca=[],zu="",Bu=function(e){var t=e[0],n,s;if(li(t)||Et(t)||(e=[e]),!(n=(t._gsap||{}).harness)){for(s=Ca.length;s--&&!Ca[s].targetTest(t););n=Ca[s]}for(s=e.length;s--;)e[s]&&(e[s]._gsap||(e[s]._gsap=new $m(e[s],n)))||e.splice(s,1);return e},Os=function(e){return e._gsap||Bu(Fn(e))[0]._gsap},wm=function(e,t,n){return(n=e[t])&&Et(n)?e[t]():Uu(n)&&e.getAttribute&&e.getAttribute(t)||n},hn=function(e,t){return(e=e.split(",")).forEach(t)||e},wt=function(e){return Math.round(e*1e5)/1e5||0},vt=function(e){return Math.round(e*1e7)/1e7||0},Er=function(e,t){var n=t.charAt(0),s=parseFloat(t.substr(2));return e=parseFloat(e),n==="+"?e+s:n==="-"?e-s:n==="*"?e*s:e/s},Cb=function(e,t){for(var n=t.length,s=0;e.indexOf(t[s])<0&&++s<n;);return s<n},$a=function(){var e=ts.length,t=ts.slice(0),n,s;for(jc={},ts.length=0,n=0;n<e;n++)s=t[n],s&&s._lazy&&(s.render(s._lazy[0],s._lazy[1],!0)._lazy=0)},ku=function(e){return!!(e._initted||e._startAt||e.add)},Rm=function(e,t,n,s){ts.length&&!Ht&&$a(),e.render(t,n,!!(Ht&&t<0&&ku(e))),ts.length&&!Ht&&$a()},Cm=function(e){var t=parseFloat(e);return(t||t===0)&&(e+"").match(Tb).length<2?t:zt(e)?e.trim():e},Pm=function(e){return e},Rn=function(e,t){for(var n in t)n in e||(e[n]=t[n]);return e},Pb=function(e){return function(t,n){for(var s in n)s in t||s==="duration"&&e||s==="ease"||(t[s]=n[s])}},Dr=function(e,t){for(var n in t)e[n]=t[n];return e},pd=function i(e,t){for(var n in t)n!=="__proto__"&&n!=="constructor"&&n!=="prototype"&&(e[n]=li(t[n])?i(e[n]||(e[n]={}),t[n]):t[n]);return e},ja=function(e,t){var n={},s;for(s in e)s in t||(n[s]=e[s]);return n},uo=function(e){var t=e.parent||xt,n=e.keyframes?Pb(jt(e.keyframes)):Rn;if(fn(e.inherit))for(;t;)n(e,t.vars.defaults),t=t.parent||t._dp;return e},Lb=function(e,t){for(var n=e.length,s=n===t.length;s&&n--&&e[n]===t[n];);return n<0},Lm=function(e,t,n,s,r){var o=e[s],a;if(r)for(a=t[r];o&&o[r]>a;)o=o._prev;return o?(t._next=o._next,o._next=t):(t._next=e[n],e[n]=t),t._next?t._next._prev=t:e[s]=t,t._prev=o,t.parent=t._dp=e,t},yl=function(e,t,n,s){n===void 0&&(n="_first"),s===void 0&&(s="_last");var r=t._prev,o=t._next;r?r._next=o:e[n]===t&&(e[n]=o),o?o._prev=r:e[s]===t&&(e[s]=r),t._next=t._prev=t.parent=null},os=function(e,t){e.parent&&(!t||e.parent.autoRemoveChildren)&&e.parent.remove&&e.parent.remove(e),e._act=0},Ns=function(e,t){if(e&&(!t||t._end>e._dur||t._start<0))for(var n=e;n;)n._dirty=1,n=n.parent;return e},Db=function(e){for(var t=e.parent;t&&t.parent;)t._dirty=1,t.totalDuration(),t=t.parent;return e},Kc=function(e,t,n,s){return e._startAt&&(Ht?e._startAt.revert(Ra):e.vars.immediateRender&&!e.vars.autoRevert||e._startAt.render(t,!0,s))},Ub=function i(e){return!e||e._ts&&i(e.parent)},md=function(e){return e._repeat?Ur(e._tTime,e=e.duration()+e._rDelay)*e:0},Ur=function(e,t){var n=Math.floor(e=vt(e/t));return e&&n===e?n-1:n},Ka=function(e,t){return(e-t._start)*t._ts+(t._ts>=0?0:t._dirty?t.totalDuration():t._tDur)},Sl=function(e){return e._end=vt(e._start+(e._tDur/Math.abs(e._ts||e._rts||ft)||0))},Ml=function(e,t){var n=e._dp;return n&&n.smoothChildTiming&&e._ts&&(e._start=vt(n._time-(e._ts>0?t/e._ts:((e._dirty?e.totalDuration():e._tDur)-t)/-e._ts)),Sl(e),n._dirty||Ns(n,e)),e},Dm=function(e,t){var n;if((t._time||!t._dur&&t._initted||t._start<e._time&&(t._dur||!t.add))&&(n=Ka(e.rawTime(),t),(!t._dur||zo(0,t.totalDuration(),n)-t._tTime>ft)&&t.render(n,!0)),Ns(e,t)._dp&&e._initted&&e._time>=e._dur&&e._ts){if(e._dur<e.duration())for(n=e;n._dp;)n.rawTime()>=0&&n.totalTime(n._tTime),n=n._dp;e._zTime=-ft}},ii=function(e,t,n,s){return t.parent&&os(t),t._start=vt((Ui(n)?n:n||e!==xt?Ln(e,n,t):e._time)+t._delay),t._end=vt(t._start+(t.totalDuration()/Math.abs(t.timeScale())||0)),Lm(e,t,"_first","_last",e._sort?"_start":0),Zc(t)||(e._recent=t),s||Dm(e,t),e._ts<0&&Ml(e,e._tTime),e},Um=function(e,t){return(wn.ScrollTrigger||Nu("scrollTrigger",t))&&wn.ScrollTrigger.create(t,e)},Im=function(e,t,n,s,r){if(Hu(e,t,r),!e._initted)return 1;if(!n&&e._pt&&!Ht&&(e._dur&&e.vars.lazy!==!1||!e._dur&&e.vars.lazy)&&Am!==yn.frame)return ts.push(e),e._lazy=[r,s],1},Ib=function i(e){var t=e.parent;return t&&t._ts&&t._initted&&!t._lock&&(t.rawTime()<0||i(t))},Zc=function(e){var t=e.data;return t==="isFromStart"||t==="isStart"},Ob=function(e,t,n,s){var r=e.ratio,o=t<0||!t&&(!e._start&&Ib(e)&&!(!e._initted&&Zc(e))||(e._ts<0||e._dp._ts<0)&&!Zc(e))?0:1,a=e._rDelay,l=0,c,u,f;if(a&&e._repeat&&(l=zo(0,e._tDur,t),u=Ur(l,a),e._yoyo&&u&1&&(o=1-o),u!==Ur(e._tTime,a)&&(r=1-o,e.vars.repeatRefresh&&e._initted&&e.invalidate())),o!==r||Ht||s||e._zTime===ft||!t&&e._zTime){if(!e._initted&&Im(e,t,s,n,l))return;for(f=e._zTime,e._zTime=t||(n?ft:0),n||(n=t&&!f),e.ratio=o,e._from&&(o=1-o),e._time=0,e._tTime=l,c=e._pt;c;)c.r(o,c.d),c=c._next;t<0&&Kc(e,t,n,!0),e._onUpdate&&!n&&Mn(e,"onUpdate"),l&&e._repeat&&!n&&e.parent&&Mn(e,"onRepeat"),(t>=e._tDur||t<0)&&e.ratio===o&&(o&&os(e,1),!n&&!Ht&&(Mn(e,o?"onComplete":"onReverseComplete",!0),e._prom&&e._prom()))}else e._zTime||(e._zTime=t)},Nb=function(e,t,n){var s;if(n>t)for(s=e._first;s&&s._start<=n;){if(s.data==="isPause"&&s._start>t)return s;s=s._next}else for(s=e._last;s&&s._start>=n;){if(s.data==="isPause"&&s._start<t)return s;s=s._prev}},Ir=function(e,t,n,s){var r=e._repeat,o=vt(t)||0,a=e._tTime/e._tDur;return a&&!s&&(e._time*=o/e._dur),e._dur=o,e._tDur=r?r<0?1e10:vt(o*(r+1)+e._rDelay*r):o,a>0&&!s&&Ml(e,e._tTime=e._tDur*a),e.parent&&Sl(e),n||Ns(e.parent,e),e},_d=function(e){return e instanceof cn?Ns(e):Ir(e,e._dur)},Fb={_start:0,endTime:bo,totalDuration:bo},Ln=function i(e,t,n){var s=e.labels,r=e._recent||Fb,o=e.duration()>=Nn?r.endTime(!1):e._dur,a,l,c;return zt(t)&&(isNaN(t)||t in s)?(l=t.charAt(0),c=t.substr(-1)==="%",a=t.indexOf("="),l==="<"||l===">"?(a>=0&&(t=t.replace(/=/,"")),(l==="<"?r._start:r.endTime(r._repeat>=0))+(parseFloat(t.substr(1))||0)*(c?(a<0?r:n).totalDuration()/100:1)):a<0?(t in s||(s[t]=o),s[t]):(l=parseFloat(t.charAt(a-1)+t.substr(a+1)),c&&n&&(l=l/100*(jt(n)?n[0]:n).totalDuration()),a>1?i(e,t.substr(0,a-1),n)+l:o+l)):t==null?o:+t},fo=function(e,t,n){var s=Ui(t[1]),r=(s?2:1)+(e<2?0:1),o=t[r],a,l;if(s&&(o.duration=t[1]),o.parent=n,e){for(a=o,l=n;l&&!("immediateRender"in a);)a=l.vars.defaults||{},l=fn(l.vars.inherit)&&l.parent;o.immediateRender=fn(a.immediateRender),e<2?o.runBackwards=1:o.startAt=t[r-1]}return new Pt(t[0],o,t[r+1])},cs=function(e,t){return e||e===0?t(e):t},zo=function(e,t,n){return n<e?e:n>t?t:n},Yt=function(e,t){return!zt(e)||!(t=Ab.exec(e))?"":t[1]},zb=function(e,t,n){return cs(n,function(s){return zo(e,t,s)})},Jc=[].slice,Om=function(e,t){return e&&li(e)&&"length"in e&&(!t&&!e.length||e.length-1 in e&&li(e[0]))&&!e.nodeType&&e!==Jn},Bb=function(e,t,n){return n===void 0&&(n=[]),e.forEach(function(s){var r;return zt(s)&&!t||Om(s,1)?(r=n).push.apply(r,Fn(s)):n.push(s)})||n},Fn=function(e,t,n){return _t&&!t&&_t.selector?_t.selector(e):zt(e)&&!n&&($c||!Or())?Jc.call((t||Ou).querySelectorAll(e),0):jt(e)?Bb(e,n):Om(e)?Jc.call(e,0):e?[e]:[]},Qc=function(e){return e=Fn(e)[0]||Eo("Invalid scope")||{},function(t){var n=e.current||e.nativeElement||e;return Fn(t,n.querySelectorAll?n:n===e?Eo("Invalid scope")||Ou.createElement("div"):e)}},Nm=function(e){return e.sort(function(){return .5-Math.random()})},Fm=function(e){if(Et(e))return e;var t=li(e)?e:{each:e},n=Fs(t.ease),s=t.from||0,r=parseFloat(t.base)||0,o={},a=s>0&&s<1,l=isNaN(s)||a,c=t.axis,u=s,f=s;return zt(s)?u=f={center:.5,edges:.5,end:1}[s]||0:!a&&l&&(u=s[0],f=s[1]),function(h,d,g){var _=(g||t).length,m=o[_],p,x,y,S,R,L,w,B,v;if(!m){if(v=t.grid==="auto"?0:(t.grid||[1,Nn])[1],!v){for(w=-Nn;w<(w=g[v++].getBoundingClientRect().left)&&v<_;);v<_&&v--}for(m=o[_]=[],p=l?Math.min(v,_)*u-.5:s%v,x=v===Nn?0:l?_*f/v-.5:s/v|0,w=0,B=Nn,L=0;L<_;L++)y=L%v-p,S=x-(L/v|0),m[L]=R=c?Math.abs(c==="y"?S:y):xm(y*y+S*S),R>w&&(w=R),R<B&&(B=R);s==="random"&&Nm(m),m.max=w-B,m.min=B,m.v=_=(parseFloat(t.amount)||parseFloat(t.each)*(v>_?_-1:c?c==="y"?_/v:v:Math.max(v,_/v))||0)*(s==="edges"?-1:1),m.b=_<0?r-_:r,m.u=Yt(t.amount||t.each)||0,n=n&&_<0?Jb(n):n}return _=(m[h]-m.min)/m.max||0,vt(m.b+(n?n(_):_)*m.v)+m.u}},eu=function(e){var t=Math.pow(10,((e+"").split(".")[1]||"").length);return function(n){var s=vt(Math.round(parseFloat(n)/e)*e*t);return(s-s%1)/t+(Ui(n)?0:Yt(n))}},zm=function(e,t){var n=jt(e),s,r;return!n&&li(e)&&(s=n=e.radius||Nn,e.values?(e=Fn(e.values),(r=!Ui(e[0]))&&(s*=s)):e=eu(e.increment)),cs(t,n?Et(e)?function(o){return r=e(o),Math.abs(r-o)<=s?r:o}:function(o){for(var a=parseFloat(r?o.x:o),l=parseFloat(r?o.y:0),c=Nn,u=0,f=e.length,h,d;f--;)r?(h=e[f].x-a,d=e[f].y-l,h=h*h+d*d):h=Math.abs(e[f]-a),h<c&&(c=h,u=f);return u=!s||c<=s?e[u]:o,r||u===o||Ui(o)?u:u+Yt(o)}:eu(e))},Bm=function(e,t,n,s){return cs(jt(e)?!t:n===!0?!!(n=0):!s,function(){return jt(e)?e[~~(Math.random()*e.length)]:(n=n||1e-5)&&(s=n<1?Math.pow(10,(n+"").length-2):1)&&Math.floor(Math.round((e-n/2+Math.random()*(t-e+n*.99))/n)*n*s)/s})},kb=function(){for(var e=arguments.length,t=new Array(e),n=0;n<e;n++)t[n]=arguments[n];return function(s){return t.reduce(function(r,o){return o(r)},s)}},Vb=function(e,t){return function(n){return e(parseFloat(n))+(t||Yt(n))}},Hb=function(e,t,n){return Vm(e,t,0,1,n)},km=function(e,t,n){return cs(n,function(s){return e[~~t(s)]})},Gb=function i(e,t,n){var s=t-e;return jt(e)?km(e,i(0,e.length),t):cs(n,function(r){return(s+(r-e)%s)%s+e})},Wb=function i(e,t,n){var s=t-e,r=s*2;return jt(e)?km(e,i(0,e.length-1),t):cs(n,function(o){return o=(r+(o-e)%r)%r||0,e+(o>s?r-o:o)})},To=function(e){return e.replace(Eb,function(t){var n=t.indexOf("[")+1,s=t.substring(n||7,n?t.indexOf("]"):t.length-1).split(bb);return Bm(n?s:+s[0],n?0:+s[1],+s[2]||1e-5)})},Vm=function(e,t,n,s,r){var o=t-e,a=s-n;return cs(r,function(l){return n+((l-e)/o*a||0)})},Xb=function i(e,t,n,s){var r=isNaN(e+t)?0:function(d){return(1-d)*e+d*t};if(!r){var o=zt(e),a={},l,c,u,f,h;if(n===!0&&(s=1)&&(n=null),o)e={p:e},t={p:t};else if(jt(e)&&!jt(t)){for(u=[],f=e.length,h=f-2,c=1;c<f;c++)u.push(i(e[c-1],e[c]));f--,r=function(g){g*=f;var _=Math.min(h,~~g);return u[_](g-_)},n=t}else s||(e=Dr(jt(e)?[]:{},e));if(!u){for(l in t)Vu.call(a,e,l,"get",t[l]);r=function(g){return Xu(g,a)||(o?e.p:e)}}}return cs(n,r)},gd=function(e,t,n){var s=e.labels,r=Nn,o,a,l;for(o in s)a=s[o]-t,a<0==!!n&&a&&r>(a=Math.abs(a))&&(l=o,r=a);return l},Mn=function(e,t,n){var s=e.vars,r=s[t],o=_t,a=e._ctx,l,c,u;if(r)return l=s[t+"Params"],c=s.callbackScope||e,n&&ts.length&&$a(),a&&(_t=a),u=l?r.apply(c,l):r.call(c),_t=o,u},Qr=function(e){return os(e),e.scrollTrigger&&e.scrollTrigger.kill(!!Ht),e.progress()<1&&Mn(e,"onInterrupt"),e},pr,Hm=[],Gm=function(e){if(e)if(e=!e.name&&e.default||e,Iu()||e.headless){var t=e.name,n=Et(e),s=t&&!n&&e.init?function(){this._props=[]}:e,r={init:bo,render:Xu,add:Vu,kill:lT,modifier:aT,rawVars:0},o={targetTest:0,get:0,getSetter:Wu,aliases:{},register:0};if(Or(),e!==s){if(xn[t])return;Rn(s,Rn(ja(e,r),o)),Dr(s.prototype,Dr(r,ja(e,o))),xn[s.prop=t]=s,e.targetTest&&(Ca.push(s),Fu[t]=1),t=(t==="css"?"CSS":t.charAt(0).toUpperCase()+t.substr(1))+"Plugin"}Tm(t,s),e.register&&e.register(mn,s,dn)}else Hm.push(e)},ut=255,eo={aqua:[0,ut,ut],lime:[0,ut,0],silver:[192,192,192],black:[0,0,0],maroon:[128,0,0],teal:[0,128,128],blue:[0,0,ut],navy:[0,0,128],white:[ut,ut,ut],olive:[128,128,0],yellow:[ut,ut,0],orange:[ut,165,0],gray:[128,128,128],purple:[128,0,128],green:[0,128,0],red:[ut,0,0],pink:[ut,192,203],cyan:[0,ut,ut],transparent:[ut,ut,ut,0]},gc=function(e,t,n){return e+=e<0?1:e>1?-1:0,(e*6<1?t+(n-t)*e*6:e<.5?n:e*3<2?t+(n-t)*(2/3-e)*6:t)*ut+.5|0},Wm=function(e,t,n){var s=e?Ui(e)?[e>>16,e>>8&ut,e&ut]:0:eo.black,r,o,a,l,c,u,f,h,d,g;if(!s){if(e.substr(-1)===","&&(e=e.substr(0,e.length-1)),eo[e])s=eo[e];else if(e.charAt(0)==="#"){if(e.length<6&&(r=e.charAt(1),o=e.charAt(2),a=e.charAt(3),e="#"+r+r+o+o+a+a+(e.length===5?e.charAt(4)+e.charAt(4):"")),e.length===9)return s=parseInt(e.substr(1,6),16),[s>>16,s>>8&ut,s&ut,parseInt(e.substr(7),16)/255];e=parseInt(e.substr(1),16),s=[e>>16,e>>8&ut,e&ut]}else if(e.substr(0,3)==="hsl"){if(s=g=e.match(hd),!t)l=+s[0]%360/360,c=+s[1]/100,u=+s[2]/100,o=u<=.5?u*(c+1):u+c-u*c,r=u*2-o,s.length>3&&(s[3]*=1),s[0]=gc(l+1/3,r,o),s[1]=gc(l,r,o),s[2]=gc(l-1/3,r,o);else if(~e.indexOf("="))return s=e.match(Sm),n&&s.length<4&&(s[3]=1),s}else s=e.match(hd)||eo.transparent;s=s.map(Number)}return t&&!g&&(r=s[0]/ut,o=s[1]/ut,a=s[2]/ut,f=Math.max(r,o,a),h=Math.min(r,o,a),u=(f+h)/2,f===h?l=c=0:(d=f-h,c=u>.5?d/(2-f-h):d/(f+h),l=f===r?(o-a)/d+(o<a?6:0):f===o?(a-r)/d+2:(r-o)/d+4,l*=60),s[0]=~~(l+.5),s[1]=~~(c*100+.5),s[2]=~~(u*100+.5)),n&&s.length<4&&(s[3]=1),s},Xm=function(e){var t=[],n=[],s=-1;return e.split(ns).forEach(function(r){var o=r.match(dr)||[];t.push.apply(t,o),n.push(s+=o.length+1)}),t.c=n,t},vd=function(e,t,n){var s="",r=(e+s).match(ns),o=t?"hsla(":"rgba(",a=0,l,c,u,f;if(!r)return e;if(r=r.map(function(h){return(h=Wm(h,t,1))&&o+(t?h[0]+","+h[1]+"%,"+h[2]+"%,"+h[3]:h.join(","))+")"}),n&&(u=Xm(e),l=n.c,l.join(s)!==u.c.join(s)))for(c=e.replace(ns,"1").split(dr),f=c.length-1;a<f;a++)s+=c[a]+(~l.indexOf(a)?r.shift()||o+"0,0,0,0)":(u.length?u:r.length?r:n).shift());if(!c)for(c=e.split(ns),f=c.length-1;a<f;a++)s+=c[a]+r[a];return s+c[f]},ns=function(){var i="(?:\\b(?:(?:rgb|rgba|hsl|hsla)\\(.+?\\))|\\B#(?:[0-9a-f]{3,4}){1,2}\\b",e;for(e in eo)i+="|"+e+"\\b";return new RegExp(i+")","gi")}(),qb=/hsl[a]?\(/,qm=function(e){var t=e.join(" "),n;if(ns.lastIndex=0,ns.test(t))return n=qb.test(t),e[1]=vd(e[1],n),e[0]=vd(e[0],n,Xm(e[1])),!0},Ao,yn=function(){var i=Date.now,e=500,t=33,n=i(),s=n,r=1e3/240,o=r,a=[],l,c,u,f,h,d,g=function _(m){var p=i()-s,x=m===!0,y,S,R,L;if((p>e||p<0)&&(n+=p-t),s+=p,R=s-n,y=R-o,(y>0||x)&&(L=++f.frame,h=R-f.time*1e3,f.time=R=R/1e3,o+=y+(y>=r?4:r-y),S=1),x||(l=c(_)),S)for(d=0;d<a.length;d++)a[d](R,h,L,m)};return f={time:0,frame:0,tick:function(){g(!0)},deltaRatio:function(m){return h/(1e3/(m||60))},wake:function(){Em&&(!$c&&Iu()&&(Jn=$c=window,Ou=Jn.document||{},wn.gsap=mn,(Jn.gsapVersions||(Jn.gsapVersions=[])).push(mn.version),bm(Ya||Jn.GreenSockGlobals||!Jn.gsap&&Jn||{}),Hm.forEach(Gm)),u=typeof requestAnimationFrame<"u"&&requestAnimationFrame,l&&f.sleep(),c=u||function(m){return setTimeout(m,o-f.time*1e3+1|0)},Ao=1,g(2))},sleep:function(){(u?cancelAnimationFrame:clearTimeout)(l),Ao=0,c=bo},lagSmoothing:function(m,p){e=m||1/0,t=Math.min(p||33,e)},fps:function(m){r=1e3/(m||240),o=f.time*1e3+r},add:function(m,p,x){var y=p?function(S,R,L,w){m(S,R,L,w),f.remove(y)}:m;return f.remove(m),a[x?"unshift":"push"](y),Or(),y},remove:function(m,p){~(p=a.indexOf(m))&&a.splice(p,1)&&d>=p&&d--},_listeners:a},f}(),Or=function(){return!Ao&&yn.wake()},et={},Yb=/^[\d.\-M][\d.\-,\s]/,$b=/["']/g,jb=function(e){for(var t={},n=e.substr(1,e.length-3).split(":"),s=n[0],r=1,o=n.length,a,l,c;r<o;r++)l=n[r],a=r!==o-1?l.lastIndexOf(","):l.length,c=l.substr(0,a),t[s]=isNaN(c)?c.replace($b,"").trim():+c,s=l.substr(a+1).trim();return t},Kb=function(e){var t=e.indexOf("(")+1,n=e.indexOf(")"),s=e.indexOf("(",t);return e.substring(t,~s&&s<n?e.indexOf(")",n+1):n)},Zb=function(e){var t=(e+"").split("("),n=et[t[0]];return n&&t.length>1&&n.config?n.config.apply(null,~e.indexOf("{")?[jb(t[1])]:Kb(e).split(",").map(Cm)):et._CE&&Yb.test(e)?et._CE("",e):n},Jb=function(e){return function(t){return 1-e(1-t)}},Fs=function(e,t){return e&&(Et(e)?e:et[e]||Zb(e))||t},Gs=function(e,t,n,s){n===void 0&&(n=function(l){return 1-t(1-l)}),s===void 0&&(s=function(l){return l<.5?t(l*2)/2:1-t((1-l)*2)/2});var r={easeIn:t,easeOut:n,easeInOut:s},o;return hn(e,function(a){et[a]=wn[a]=r,et[o=a.toLowerCase()]=n;for(var l in r)et[o+(l==="easeIn"?".in":l==="easeOut"?".out":".inOut")]=et[a+"."+l]=r[l]}),r},Ym=function(e){return function(t){return t<.5?(1-e(1-t*2))/2:.5+e((t-.5)*2)/2}},vc=function i(e,t,n){var s=t>=1?t:1,r=(n||(e?.3:.45))/(t<1?t:1),o=r/Yc*(Math.asin(1/s)||0),a=function(u){return u===1?1:s*Math.pow(2,-10*u)*Mb((u-o)*r)+1},l=e==="out"?a:e==="in"?function(c){return 1-a(1-c)}:Ym(a);return r=Yc/r,l.config=function(c,u){return i(e,c,u)},l},xc=function i(e,t){t===void 0&&(t=1.70158);var n=function(o){return o?--o*o*((t+1)*o+t)+1:0},s=e==="out"?n:e==="in"?function(r){return 1-n(1-r)}:Ym(n);return s.config=function(r){return i(e,r)},s};hn("Linear,Quad,Cubic,Quart,Quint,Strong",function(i,e){var t=e<5?e+1:e;Gs(i+",Power"+(t-1),e?function(n){return Math.pow(n,t)}:function(n){return n},function(n){return 1-Math.pow(1-n,t)},function(n){return n<.5?Math.pow(n*2,t)/2:1-Math.pow((1-n)*2,t)/2})});et.Linear.easeNone=et.none=et.Linear.easeIn;Gs("Elastic",vc("in"),vc("out"),vc());(function(i,e){var t=1/e,n=2*t,s=2.5*t,r=function(a){return a<t?i*a*a:a<n?i*Math.pow(a-1.5/e,2)+.75:a<s?i*(a-=2.25/e)*a+.9375:i*Math.pow(a-2.625/e,2)+.984375};Gs("Bounce",function(o){return 1-r(1-o)},r)})(7.5625,2.75);Gs("Expo",function(i){return Math.pow(2,10*(i-1))*i+i*i*i*i*i*i*(1-i)});Gs("Circ",function(i){return-(xm(1-i*i)-1)});Gs("Sine",function(i){return i===1?1:-Sb(i*xb)+1});Gs("Back",xc("in"),xc("out"),xc());et.SteppedEase=et.steps=wn.SteppedEase={config:function(e,t){e===void 0&&(e=1);var n=1/e,s=e+(t?0:1),r=t?1:0,o=1-ft;return function(a){return((s*zo(0,o,a)|0)+r)*n}}};Mo.ease=et["quad.out"];hn("onComplete,onUpdate,onStart,onRepeat,onReverseComplete,onInterrupt",function(i){return zu+=i+","+i+"Params,"});var $m=function(e,t){this.id=yb++,e._gsap=this,this.target=e,this.harness=t,this.get=t?t.get:wm,this.set=t?t.getSetter:Wu},wo=function(){function i(t){this.vars=t,this._delay=+t.delay||0,(this._repeat=t.repeat===1/0?-2:t.repeat||0)&&(this._rDelay=t.repeatDelay||0,this._yoyo=!!t.yoyo||!!t.yoyoEase),this._ts=1,Ir(this,+t.duration,1,1),this.data=t.data,_t&&(this._ctx=_t,_t.data.push(this)),Ao||yn.wake()}var e=i.prototype;return e.delay=function(n){return n||n===0?(this.parent&&this.parent.smoothChildTiming&&this.startTime(this._start+n-this._delay),this._delay=n,this):this._delay},e.duration=function(n){return arguments.length?this.totalDuration(this._repeat>0?n+(n+this._rDelay)*this._repeat:n):this.totalDuration()&&this._dur},e.totalDuration=function(n){return arguments.length?(this._dirty=0,Ir(this,this._repeat<0?n:(n-this._repeat*this._rDelay)/(this._repeat+1))):this._tDur},e.totalTime=function(n,s){if(Or(),!arguments.length)return this._tTime;var r=this._dp;if(r&&r.smoothChildTiming&&this._ts){for(Ml(this,n),!r._dp||r.parent||Dm(r,this);r&&r.parent;)r.parent._time!==r._start+(r._ts>=0?r._tTime/r._ts:(r.totalDuration()-r._tTime)/-r._ts)&&r.totalTime(r._tTime,!0),r=r.parent;!this.parent&&this._dp.autoRemoveChildren&&(this._ts>0&&n<this._tDur||this._ts<0&&n>0||!this._tDur&&!n)&&ii(this._dp,this,this._start-this._delay)}return(this._tTime!==n||!this._dur&&!s||this._initted&&Math.abs(this._zTime)===ft||!this._initted&&this._dur&&n||!n&&!this._initted&&(this.add||this._ptLookup))&&(this._ts||(this._pTime=n),Rm(this,n,s)),this},e.time=function(n,s){return arguments.length?this.totalTime(Math.min(this.totalDuration(),n+md(this))%(this._dur+this._rDelay)||(n?this._dur:0),s):this._time},e.totalProgress=function(n,s){return arguments.length?this.totalTime(this.totalDuration()*n,s):this.totalDuration()?Math.min(1,this._tTime/this._tDur):this.rawTime()>=0&&this._initted?1:0},e.progress=function(n,s){return arguments.length?this.totalTime(this.duration()*(this._yoyo&&!(this.iteration()&1)?1-n:n)+md(this),s):this.duration()?Math.min(1,this._time/this._dur):this.rawTime()>0?1:0},e.iteration=function(n,s){var r=this.duration()+this._rDelay;return arguments.length?this.totalTime(this._time+(n-1)*r,s):this._repeat?Ur(this._tTime,r)+1:1},e.timeScale=function(n,s){if(!arguments.length)return this._rts===-ft?0:this._rts;if(this._rts===n)return this;var r=this.parent&&this._ts?Ka(this.parent._time,this):this._tTime;return this._rts=+n||0,this._ts=this._ps||n===-ft?0:this._rts,this.totalTime(zo(-Math.abs(this._delay),this.totalDuration(),r),s!==!1),Sl(this),Db(this)},e.paused=function(n){return arguments.length?(this._ps!==n&&(this._ps=n,n?(this._pTime=this._tTime||Math.max(-this._delay,this.rawTime()),this._ts=this._act=0):(Or(),this._ts=this._rts,this.totalTime(this.parent&&!this.parent.smoothChildTiming?this.rawTime():this._tTime||this._pTime,this.progress()===1&&Math.abs(this._zTime)!==ft&&(this._tTime-=ft)))),this):this._ps},e.startTime=function(n){if(arguments.length){this._start=vt(n);var s=this.parent||this._dp;return s&&(s._sort||!this.parent)&&ii(s,this,this._start-this._delay),this}return this._start},e.endTime=function(n){return this._start+(fn(n)?this.totalDuration():this.duration())/Math.abs(this._ts||1)},e.rawTime=function(n){var s=this.parent||this._dp;return s?n&&(!this._ts||this._repeat&&this._time&&this.totalProgress()<1)?this._tTime%(this._dur+this._rDelay):this._ts?Ka(s.rawTime(n),this):this._tTime:this._tTime},e.revert=function(n){n===void 0&&(n=Rb);var s=Ht;return Ht=n,ku(this)&&(this.timeline&&this.timeline.revert(n),this.totalTime(-.01,n.suppressEvents)),this.data!=="nested"&&n.kill!==!1&&this.kill(),Ht=s,this},e.globalTime=function(n){for(var s=this,r=arguments.length?n:s.rawTime();s;)r=s._start+r/(Math.abs(s._ts)||1),s=s._dp;return!this.parent&&this._sat?this._sat.globalTime(n):r},e.repeat=function(n){return arguments.length?(this._repeat=n===1/0?-2:n,_d(this)):this._repeat===-2?1/0:this._repeat},e.repeatDelay=function(n){if(arguments.length){var s=this._time;return this._rDelay=n,_d(this),s?this.time(s):this}return this._rDelay},e.yoyo=function(n){return arguments.length?(this._yoyo=n,this):this._yoyo},e.seek=function(n,s){return this.totalTime(Ln(this,n),fn(s))},e.restart=function(n,s){return this.play().totalTime(n?-this._delay:0,fn(s)),this._dur||(this._zTime=-ft),this},e.play=function(n,s){return n!=null&&this.seek(n,s),this.reversed(!1).paused(!1)},e.reverse=function(n,s){return n!=null&&this.seek(n||this.totalDuration(),s),this.reversed(!0).paused(!1)},e.pause=function(n,s){return n!=null&&this.seek(n,s),this.paused(!0)},e.resume=function(){return this.paused(!1)},e.reversed=function(n){return arguments.length?(!!n!==this.reversed()&&this.timeScale(-this._rts||(n?-ft:0)),this):this._rts<0},e.invalidate=function(){return this._initted=this._act=0,this._zTime=-ft,this},e.isActive=function(){var n=this.parent||this._dp,s=this._start,r;return!!(!n||this._ts&&this._initted&&n.isActive()&&(r=n.rawTime(!0))>=s&&r<this.endTime(!0)-ft)},e.eventCallback=function(n,s,r){var o=this.vars;return arguments.length>1?(s?(o[n]=s,r&&(o[n+"Params"]=r),n==="onUpdate"&&(this._onUpdate=s)):delete o[n],this):o[n]},e.then=function(n){var s=this,r=s._prom;return new Promise(function(o){var a=Et(n)?n:Pm,l=function(){var u=s.then;s.then=null,r&&r(),Et(a)&&(a=a(s))&&(a.then||a===s)&&(s.then=u),o(a),s.then=u};s._initted&&s.totalProgress()===1&&s._ts>=0||!s._tTime&&s._ts<0?l():s._prom=l})},e.kill=function(){Qr(this)},i}();Rn(wo.prototype,{_time:0,_start:0,_end:0,_tTime:0,_tDur:0,_dirty:0,_repeat:0,_yoyo:!1,parent:null,_initted:!1,_rDelay:0,_ts:1,_dp:0,ratio:0,_zTime:-ft,_prom:0,_ps:!1,_rts:1});var cn=function(i){vm(e,i);function e(n,s){var r;return n===void 0&&(n={}),r=i.call(this,n)||this,r.labels={},r.smoothChildTiming=!!n.smoothChildTiming,r.autoRemoveChildren=!!n.autoRemoveChildren,r._sort=fn(n.sortChildren),xt&&ii(n.parent||xt,xi(r),s),n.reversed&&r.reverse(),n.paused&&r.paused(!0),n.scrollTrigger&&Um(xi(r),n.scrollTrigger),r}var t=e.prototype;return t.to=function(s,r,o){return fo(0,arguments,this),this},t.from=function(s,r,o){return fo(1,arguments,this),this},t.fromTo=function(s,r,o,a){return fo(2,arguments,this),this},t.set=function(s,r,o){return r.duration=0,r.parent=this,uo(r).repeatDelay||(r.repeat=0),r.immediateRender=!!r.immediateRender,new Pt(s,r,Ln(this,o),1),this},t.call=function(s,r,o){return ii(this,Pt.delayedCall(0,s,r),o)},t.staggerTo=function(s,r,o,a,l,c,u){return o.duration=r,o.stagger=o.stagger||a,o.onComplete=c,o.onCompleteParams=u,o.parent=this,new Pt(s,o,Ln(this,l)),this},t.staggerFrom=function(s,r,o,a,l,c,u){return o.runBackwards=1,uo(o).immediateRender=fn(o.immediateRender),this.staggerTo(s,r,o,a,l,c,u)},t.staggerFromTo=function(s,r,o,a,l,c,u,f){return a.startAt=o,uo(a).immediateRender=fn(a.immediateRender),this.staggerTo(s,r,a,l,c,u,f)},t.render=function(s,r,o){var a=this._time,l=this._dirty?this.totalDuration():this._tDur,c=this._dur,u=s<=0?0:vt(s),f=this._zTime<0!=s<0&&(this._initted||!c),h,d,g,_,m,p,x,y,S,R,L,w;if(this!==xt&&u>l&&s>=0&&(u=l),u!==this._tTime||o||f){if(a!==this._time&&c&&(u+=this._time-a,s+=this._time-a),h=u,S=this._start,y=this._ts,p=!y,f&&(c||(a=this._zTime),(s||!r)&&(this._zTime=s)),this._repeat){if(L=this._yoyo,m=c+this._rDelay,this._repeat<-1&&s<0)return this.totalTime(m*100+s,r,o);if(h=vt(u%m),u===l?(_=this._repeat,h=c):(R=vt(u/m),_=~~R,_&&_===R&&(h=c,_--),h>c&&(h=c)),R=Ur(this._tTime,m),!a&&this._tTime&&R!==_&&this._tTime-R*m-this._dur<=0&&(R=_),L&&_&1&&(h=c-h,w=1),_!==R&&!this._lock){var B=L&&R&1,v=B===(L&&_&1);if(_<R&&(B=!B),a=B?0:u%c?c:u,this._lock=1,this.render(a||(w?0:vt(_*m)),r,!c)._lock=0,this._tTime=u,!r&&this.parent&&Mn(this,"onRepeat"),this.vars.repeatRefresh&&!w&&(this.invalidate()._lock=1,R=_),a&&a!==this._time||p!==!this._ts||this.vars.onRepeat&&!this.parent&&!this._act)return this;if(c=this._dur,l=this._tDur,v&&(this._lock=2,a=B?c:-1e-4,this.render(a,!0),this.vars.repeatRefresh&&!w&&this.invalidate()),this._lock=0,!this._ts&&!p)return this}}if(this._hasPause&&!this._forcing&&this._lock<2&&(x=Nb(this,vt(a),vt(h)),x&&(u-=h-(h=x._start))),this._tTime=u,this._time=h,this._act=!!y,this._initted||(this._onUpdate=this.vars.onUpdate,this._initted=1,this._zTime=s,a=0),!a&&u&&c&&!r&&!R&&(Mn(this,"onStart"),this._tTime!==u))return this;if(h>=a&&s>=0)for(d=this._first;d;){if(g=d._next,(d._act||h>=d._start)&&d._ts&&x!==d){if(d.parent!==this)return this.render(s,r,o);if(d.render(d._ts>0?(h-d._start)*d._ts:(d._dirty?d.totalDuration():d._tDur)+(h-d._start)*d._ts,r,o),h!==this._time||!this._ts&&!p){x=0,g&&(u+=this._zTime=-ft);break}}d=g}else{d=this._last;for(var b=s<0?s:h;d;){if(g=d._prev,(d._act||b<=d._end)&&d._ts&&x!==d){if(d.parent!==this)return this.render(s,r,o);if(d.render(d._ts>0?(b-d._start)*d._ts:(d._dirty?d.totalDuration():d._tDur)+(b-d._start)*d._ts,r,o||Ht&&ku(d)),h!==this._time||!this._ts&&!p){x=0,g&&(u+=this._zTime=b?-ft:ft);break}}d=g}}if(x&&!r&&(this.pause(),x.render(h>=a?0:-ft)._zTime=h>=a?1:-1,this._ts))return this._start=S,Sl(this),this.render(s,r,o);this._onUpdate&&!r&&Mn(this,"onUpdate",!0),(u===l&&this._tTime>=this.totalDuration()||!u&&a)&&(S===this._start||Math.abs(y)!==Math.abs(this._ts))&&(this._lock||((s||!c)&&(u===l&&this._ts>0||!u&&this._ts<0)&&os(this,1),!r&&!(s<0&&!a)&&(u||a||!l)&&(Mn(this,u===l&&s>=0?"onComplete":"onReverseComplete",!0),this._prom&&!(u<l&&this.timeScale()>0)&&this._prom())))}return this},t.add=function(s,r){var o=this;if(Ui(r)||(r=Ln(this,r,s)),!(s instanceof wo)){if(jt(s))return s.forEach(function(a){return o.add(a,r)}),this;if(zt(s))return this.addLabel(s,r);if(Et(s))s=Pt.delayedCall(0,s);else return this}return this!==s?ii(this,s,r):this},t.getChildren=function(s,r,o,a){s===void 0&&(s=!0),r===void 0&&(r=!0),o===void 0&&(o=!0),a===void 0&&(a=-Nn);for(var l=[],c=this._first;c;)c._start>=a&&(c instanceof Pt?r&&l.push(c):(o&&l.push(c),s&&l.push.apply(l,c.getChildren(!0,r,o)))),c=c._next;return l},t.getById=function(s){for(var r=this.getChildren(1,1,1),o=r.length;o--;)if(r[o].vars.id===s)return r[o]},t.remove=function(s){return zt(s)?this.removeLabel(s):Et(s)?this.killTweensOf(s):(s.parent===this&&yl(this,s),s===this._recent&&(this._recent=this._last),Ns(this))},t.totalTime=function(s,r){return arguments.length?(this._forcing=1,!this._dp&&this._ts&&(this._start=vt(yn.time-(this._ts>0?s/this._ts:(this.totalDuration()-s)/-this._ts))),i.prototype.totalTime.call(this,s,r),this._forcing=0,this):this._tTime},t.addLabel=function(s,r){return this.labels[s]=Ln(this,r),this},t.removeLabel=function(s){return delete this.labels[s],this},t.addPause=function(s,r,o){var a=Pt.delayedCall(0,r||bo,o);return a.data="isPause",this._hasPause=1,ii(this,a,Ln(this,s))},t.removePause=function(s){var r=this._first;for(s=Ln(this,s);r;)r._start===s&&r.data==="isPause"&&os(r),r=r._next},t.killTweensOf=function(s,r,o){for(var a=this.getTweensOf(s,o),l=a.length;l--;)$i!==a[l]&&a[l].kill(s,r);return this},t.getTweensOf=function(s,r){for(var o=[],a=Fn(s),l=this._first,c=Ui(r),u;l;)l instanceof Pt?Cb(l._targets,a)&&(c?(!$i||l._initted&&l._ts)&&l.globalTime(0)<=r&&l.globalTime(l.totalDuration())>r:!r||l.isActive())&&o.push(l):(u=l.getTweensOf(a,r)).length&&o.push.apply(o,u),l=l._next;return o},t.tweenTo=function(s,r){r=r||{};var o=this,a=Ln(o,s),l=r,c=l.startAt,u=l.onStart,f=l.onStartParams,h=l.immediateRender,d,g=Pt.to(o,Rn({ease:r.ease||"none",lazy:!1,immediateRender:!1,time:a,overwrite:"auto",duration:r.duration||Math.abs((a-(c&&"time"in c?c.time:o._time))/o.timeScale())||ft,onStart:function(){if(o.pause(),!d){var m=r.duration||Math.abs((a-(c&&"time"in c?c.time:o._time))/o.timeScale());g._dur!==m&&Ir(g,m,0,1).render(g._time,!0,!0),d=1}u&&u.apply(g,f||[])}},r));return h?g.render(0):g},t.tweenFromTo=function(s,r,o){return this.tweenTo(r,Rn({startAt:{time:Ln(this,s)}},o))},t.recent=function(){return this._recent},t.nextLabel=function(s){return s===void 0&&(s=this._time),gd(this,Ln(this,s))},t.previousLabel=function(s){return s===void 0&&(s=this._time),gd(this,Ln(this,s),1)},t.currentLabel=function(s){return arguments.length?this.seek(s,!0):this.previousLabel(this._time+ft)},t.shiftChildren=function(s,r,o){o===void 0&&(o=0);var a=this._first,l=this.labels,c;for(s=vt(s);a;)a._start>=o&&(a._start+=s,a._end+=s),a=a._next;if(r)for(c in l)l[c]>=o&&(l[c]+=s);return Ns(this)},t.invalidate=function(s){var r=this._first;for(this._lock=0;r;)r.invalidate(s),r=r._next;return i.prototype.invalidate.call(this,s)},t.clear=function(s){s===void 0&&(s=!0);for(var r=this._first,o;r;)o=r._next,this.remove(r),r=o;return this._dp&&(this._time=this._tTime=this._pTime=0),s&&(this.labels={}),Ns(this)},t.totalDuration=function(s){var r=0,o=this,a=o._last,l=Nn,c,u,f;if(arguments.length)return o.timeScale((o._repeat<0?o.duration():o.totalDuration())/(o.reversed()?-s:s));if(o._dirty){for(f=o.parent;a;)c=a._prev,a._dirty&&a.totalDuration(),u=a._start,u>l&&o._sort&&a._ts&&!o._lock?(o._lock=1,ii(o,a,u-a._delay,1)._lock=0):l=u,u<0&&a._ts&&(r-=u,(!f&&!o._dp||f&&f.smoothChildTiming)&&(o._start+=vt(u/o._ts),o._time-=u,o._tTime-=u),o.shiftChildren(-u,!1,-1/0),l=0),a._end>r&&a._ts&&(r=a._end),a=c;Ir(o,o===xt&&o._time>r?o._time:r,1,1),o._dirty=0}return o._tDur},e.updateRoot=function(s){if(xt._ts&&(Rm(xt,Ka(s,xt)),Am=yn.frame),yn.frame>=dd){dd+=An.autoSleep||120;var r=xt._first;if((!r||!r._ts)&&An.autoSleep&&yn._listeners.length<2){for(;r&&!r._ts;)r=r._next;r||yn.sleep()}}},e}(wo);Rn(cn.prototype,{_lock:0,_hasPause:0,_forcing:0});var Qb=function(e,t,n,s,r,o,a){var l=new dn(this._pt,e,t,0,1,e_,null,r),c=0,u=0,f,h,d,g,_,m,p,x;for(l.b=n,l.e=s,n+="",s+="",(p=~s.indexOf("random("))&&(s=To(s)),o&&(x=[n,s],o(x,e,t),n=x[0],s=x[1]),h=n.match(mc)||[];f=mc.exec(s);)g=f[0],_=s.substring(c,f.index),d?d=(d+1)%5:_.substr(-5)==="rgba("&&(d=1),g!==h[u++]&&(m=parseFloat(h[u-1])||0,l._pt={_next:l._pt,p:_||u===1?_:",",s:m,c:g.charAt(1)==="="?Er(m,g)-m:parseFloat(g)-m,m:d&&d<4?Math.round:0},c=mc.lastIndex);return l.c=c<s.length?s.substring(c,s.length):"",l.fp=a,(Mm.test(s)||p)&&(l.e=0),this._pt=l,l},Vu=function(e,t,n,s,r,o,a,l,c,u){Et(s)&&(s=s(r||0,e,o));var f=e[t],h=n!=="get"?n:Et(f)?c?e[t.indexOf("set")||!Et(e["get"+t.substr(3)])?t:"get"+t.substr(3)](c):e[t]():f,d=Et(f)?c?sT:Jm:Gu,g;if(zt(s)&&(~s.indexOf("random(")&&(s=To(s)),s.charAt(1)==="="&&(g=Er(h,s)+(Yt(h)||0),(g||g===0)&&(s=g))),!u||h!==s||tu)return!isNaN(h*s)&&s!==""?(g=new dn(this._pt,e,t,+h||0,s-(h||0),typeof f=="boolean"?oT:Qm,0,d),c&&(g.fp=c),a&&g.modifier(a,this,e),this._pt=g):(!f&&!(t in e)&&Nu(t,s),Qb.call(this,e,t,h,s,d,l||An.stringFilter,c))},eT=function(e,t,n,s,r){if(Et(e)&&(e=ho(e,r,t,n,s)),!li(e)||e.style&&e.nodeType||jt(e)||ym(e))return zt(e)?ho(e,r,t,n,s):e;var o={},a;for(a in e)o[a]=ho(e[a],r,t,n,s);return o},jm=function(e,t,n,s,r,o){var a,l,c,u;if(xn[e]&&(a=new xn[e]).init(r,a.rawVars?t[e]:eT(t[e],s,r,o,n),n,s,o)!==!1&&(n._pt=l=new dn(n._pt,r,e,0,1,a.render,a,0,a.priority),n!==pr))for(c=n._ptLookup[n._targets.indexOf(r)],u=a._props.length;u--;)c[a._props[u]]=l;return a},$i,tu,Hu=function i(e,t,n){var s=e.vars,r=s.ease,o=s.startAt,a=s.immediateRender,l=s.lazy,c=s.onUpdate,u=s.runBackwards,f=s.yoyoEase,h=s.keyframes,d=s.autoRevert,g=e._dur,_=e._startAt,m=e._targets,p=e.parent,x=p&&p.data==="nested"?p.vars.targets:m,y=e._overwrite==="auto"&&!Du,S=e.timeline,R=s.easeReverse||f,L,w,B,v,b,N,A,I,O,k,H,q,Z;if(S&&(!h||!r)&&(r="none"),e._ease=Fs(r,Mo.ease),e._rEase=R&&(Fs(R)||e._ease),e._from=!S&&!!s.runBackwards,e._from&&(e.ratio=1),!S||h&&!s.stagger){if(I=m[0]?Os(m[0]).harness:0,q=I&&s[I.prop],L=ja(s,Fu),_&&(_._zTime<0&&_.progress(1),t<0&&u&&a&&!d?_.render(-1,!0):_.revert(u&&g?Ra:wb),_._lazy=0),o){if(os(e._startAt=Pt.set(m,Rn({data:"isStart",overwrite:!1,parent:p,immediateRender:!0,lazy:!_&&fn(l),startAt:null,delay:0,onUpdate:c&&function(){return Mn(e,"onUpdate")},stagger:0},o))),e._startAt._dp=0,e._startAt._sat=e,t<0&&(Ht||!a&&!d)&&e._startAt.revert(Ra),a&&g&&t<=0&&n<=0){t&&(e._zTime=t);return}}else if(u&&g&&!_){if(t&&(a=!1),B=Rn({overwrite:!1,data:"isFromStart",lazy:a&&!_&&fn(l),immediateRender:a,stagger:0,parent:p},L),q&&(B[I.prop]=q),os(e._startAt=Pt.set(m,B)),e._startAt._dp=0,e._startAt._sat=e,t<0&&(Ht?e._startAt.revert(Ra):e._startAt.render(-1,!0)),e._zTime=t,!a)i(e._startAt,ft,ft);else if(!t)return}for(e._pt=e._ptCache=0,l=g&&fn(l)||l&&!g,w=0;w<m.length;w++){if(b=m[w],A=b._gsap||Bu(m)[w]._gsap,e._ptLookup[w]=k={},jc[A.id]&&ts.length&&$a(),H=x===m?w:x.indexOf(b),I&&(O=new I).init(b,q||L,e,H,x)!==!1&&(e._pt=v=new dn(e._pt,b,O.name,0,1,O.render,O,0,O.priority),O._props.forEach(function(W){k[W]=v}),O.priority&&(N=1)),!I||q)for(B in L)xn[B]&&(O=jm(B,L,e,H,b,x))?O.priority&&(N=1):k[B]=v=Vu.call(e,b,B,"get",L[B],H,x,0,s.stringFilter);e._op&&e._op[w]&&e.kill(b,e._op[w]),y&&e._pt&&($i=e,xt.killTweensOf(b,k,e.globalTime(t)),Z=!e.parent,$i=0),e._pt&&l&&(jc[A.id]=1)}N&&t_(e),e._onInit&&e._onInit(e)}e._onUpdate=c,e._initted=(!e._op||e._pt)&&!Z,h&&t<=0&&S.render(Nn,!0,!0)},tT=function(e,t,n,s,r,o,a,l){var c=(e._pt&&e._ptCache||(e._ptCache={}))[t],u,f,h,d;if(!c)for(c=e._ptCache[t]=[],h=e._ptLookup,d=e._targets.length;d--;){if(u=h[d][t],u&&u.d&&u.d._pt)for(u=u.d._pt;u&&u.p!==t&&u.fp!==t;)u=u._next;if(!u)return tu=1,e.vars[t]="+=0",Hu(e,a),tu=0,l?Eo(t+" not eligible for reset. Try splitting into individual properties"):1;c.push(u)}for(d=c.length;d--;)f=c[d],u=f._pt||f,u.s=(s||s===0)&&!r?s:u.s+(s||0)+o*u.c,u.c=n-u.s,f.e&&(f.e=wt(n)+Yt(f.e)),f.b&&(f.b=u.s+Yt(f.b))},nT=function(e,t){var n=e[0]?Os(e[0]).harness:0,s=n&&n.aliases,r,o,a,l;if(!s)return t;r=Dr({},t);for(o in s)if(o in r)for(l=s[o].split(","),a=l.length;a--;)r[l[a]]=r[o];return r},iT=function(e,t,n,s){var r=t.ease||s||"power1.inOut",o,a;if(jt(t))a=n[e]||(n[e]=[]),t.forEach(function(l,c){return a.push({t:c/(t.length-1)*100,v:l,e:r})});else for(o in t)a=n[o]||(n[o]=[]),o==="ease"||a.push({t:parseFloat(e),v:t[o],e:r})},ho=function(e,t,n,s,r){return Et(e)?e.call(t,n,s,r):zt(e)&&~e.indexOf("random(")?To(e):e},Km=zu+"repeat,repeatDelay,yoyo,repeatRefresh,yoyoEase,easeReverse,autoRevert",Zm={};hn(Km+",id,stagger,delay,duration,paused,scrollTrigger",function(i){return Zm[i]=1});var Pt=function(i){vm(e,i);function e(n,s,r,o){var a;typeof s=="number"&&(r.duration=s,s=r,r=null),a=i.call(this,o?s:uo(s))||this;var l=a.vars,c=l.duration,u=l.delay,f=l.immediateRender,h=l.stagger,d=l.overwrite,g=l.keyframes,_=l.defaults,m=l.scrollTrigger,p=s.parent||xt,x=(jt(n)||ym(n)?Ui(n[0]):"length"in s)?[n]:Fn(n),y,S,R,L,w,B,v,b;if(a._targets=x.length?Bu(x):Eo("GSAP target "+n+" not found. https://gsap.com",!An.nullTargetWarn)||[],a._ptLookup=[],a._overwrite=d,g||h||va(c)||va(u)){s=a.vars;var N=s.easeReverse||s.yoyoEase;if(y=a.timeline=new cn({data:"nested",defaults:_||{},targets:p&&p.data==="nested"?p.vars.targets:x}),y.kill(),y.parent=y._dp=xi(a),y._start=0,h||va(c)||va(u)){if(L=x.length,v=h&&Fm(h),li(h))for(w in h)~Km.indexOf(w)&&(b||(b={}),b[w]=h[w]);for(S=0;S<L;S++)R=ja(s,Zm),R.stagger=0,N&&(R.easeReverse=N),b&&Dr(R,b),B=x[S],R.duration=+ho(c,xi(a),S,B,x),R.delay=(+ho(u,xi(a),S,B,x)||0)-a._delay,!h&&L===1&&R.delay&&(a._delay=u=R.delay,a._start+=u,R.delay=0),y.to(B,R,v?v(S,B,x):0),y._ease=et.none;y.duration()?c=u=0:a.timeline=0}else if(g){uo(Rn(y.vars.defaults,{ease:"none"})),y._ease=Fs(g.ease||s.ease||"none");var A=0,I,O,k;if(jt(g))g.forEach(function(H){return y.to(x,H,">")}),y.duration();else{R={};for(w in g)w==="ease"||w==="easeEach"||iT(w,g[w],R,g.easeEach);for(w in R)for(I=R[w].sort(function(H,q){return H.t-q.t}),A=0,S=0;S<I.length;S++)O=I[S],k={ease:O.e,duration:(O.t-(S?I[S-1].t:0))/100*c},k[w]=O.v,y.to(x,k,A),A+=k.duration;y.duration()<c&&y.to({},{duration:c-y.duration()})}}c||a.duration(c=y.duration())}else a.timeline=0;return d===!0&&!Du&&($i=xi(a),xt.killTweensOf(x),$i=0),ii(p,xi(a),r),s.reversed&&a.reverse(),s.paused&&a.paused(!0),(f||!c&&!g&&a._start===vt(p._time)&&fn(f)&&Ub(xi(a))&&p.data!=="nested")&&(a._tTime=-ft,a.render(Math.max(0,-u)||0)),m&&Um(xi(a),m),a}var t=e.prototype;return t.render=function(s,r,o){var a=this._time,l=this._tDur,c=this._dur,u=s<0,f=s>l-ft&&!u?l:s<ft?0:s,h,d,g,_,m,p,x,y;if(!c)Ob(this,s,r,o);else if(f!==this._tTime||!s||o||!this._initted&&this._tTime||this._startAt&&this._zTime<0!==u||this._lazy){if(h=f,y=this.timeline,this._repeat){if(_=c+this._rDelay,this._repeat<-1&&u)return this.totalTime(_*100+s,r,o);if(h=vt(f%_),f===l?(g=this._repeat,h=c):(m=vt(f/_),g=~~m,g&&g===m?(h=c,g--):h>c&&(h=c)),p=this._yoyo&&g&1,p&&(h=c-h),m=Ur(this._tTime,_),h===a&&!o&&this._initted&&g===m)return this._tTime=f,this;g!==m&&this.vars.repeatRefresh&&!p&&!this._lock&&h!==_&&this._initted&&(this._lock=o=1,this.render(vt(_*g),!0).invalidate()._lock=0)}if(!this._initted){if(Im(this,u?s:h,o,r,f))return this._tTime=0,this;if(a!==this._time&&!(o&&this.vars.repeatRefresh&&g!==m))return this;if(c!==this._dur)return this.render(s,r,o)}if(this._rEase){var S=h<a;if(S!==this._inv){var R=S?a:c-a;this._inv=S,this._from&&(this.ratio=1-this.ratio),this._invRatio=this.ratio,this._invTime=a,this._invRecip=R?(S?-1:1)/R:0,this._invScale=S?-this.ratio:1-this.ratio,this._invEase=S?this._rEase:this._ease}this.ratio=x=this._invRatio+this._invScale*this._invEase((h-this._invTime)*this._invRecip)}else this.ratio=x=this._ease(h/c);if(this._from&&(this.ratio=x=1-x),this._tTime=f,this._time=h,!this._act&&this._ts&&(this._act=1,this._lazy=0),!a&&f&&!r&&!m&&(Mn(this,"onStart"),this._tTime!==f))return this;for(d=this._pt;d;)d.r(x,d.d),d=d._next;y&&y.render(s<0?s:y._dur*y._ease(h/this._dur),r,o)||this._startAt&&(this._zTime=s),this._onUpdate&&!r&&(u&&Kc(this,s,r,o),Mn(this,"onUpdate")),this._repeat&&g!==m&&this.vars.onRepeat&&!r&&this.parent&&Mn(this,"onRepeat"),(f===this._tDur||!f)&&this._tTime===f&&(u&&!this._onUpdate&&Kc(this,s,!0,!0),(s||!c)&&(f===this._tDur&&this._ts>0||!f&&this._ts<0)&&os(this,1),!r&&!(u&&!a)&&(f||a||p)&&(Mn(this,f===l?"onComplete":"onReverseComplete",!0),this._prom&&!(f<l&&this.timeScale()>0)&&this._prom()))}return this},t.targets=function(){return this._targets},t.invalidate=function(s){return(!s||!this.vars.runBackwards)&&(this._startAt=0),this._pt=this._op=this._onUpdate=this._lazy=this.ratio=0,this._ptLookup=[],this.timeline&&this.timeline.invalidate(s),i.prototype.invalidate.call(this,s)},t.resetTo=function(s,r,o,a,l){Ao||yn.wake(),this._ts||this.play();var c=Math.min(this._dur,(this._dp._time-this._start)*this._ts),u;return this._initted||Hu(this,c),u=this._ease(c/this._dur),tT(this,s,r,o,a,u,c,l)?this.resetTo(s,r,o,a,1):(Ml(this,0),this.parent||Lm(this._dp,this,"_first","_last",this._dp._sort?"_start":0),this.render(0))},t.kill=function(s,r){if(r===void 0&&(r="all"),!s&&(!r||r==="all"))return this._lazy=this._pt=0,this.parent?Qr(this):this.scrollTrigger&&this.scrollTrigger.kill(!!Ht),this;if(this.timeline){var o=this.timeline.totalDuration();return this.timeline.killTweensOf(s,r,$i&&$i.vars.overwrite!==!0)._first||Qr(this),this.parent&&o!==this.timeline.totalDuration()&&Ir(this,this._dur*this.timeline._tDur/o,0,1),this}var a=this._targets,l=s?Fn(s):a,c=this._ptLookup,u=this._pt,f,h,d,g,_,m,p;if((!r||r==="all")&&Lb(a,l))return r==="all"&&(this._pt=0),Qr(this);for(f=this._op=this._op||[],r!=="all"&&(zt(r)&&(_={},hn(r,function(x){return _[x]=1}),r=_),r=nT(a,r)),p=a.length;p--;)if(~l.indexOf(a[p])){h=c[p],r==="all"?(f[p]=r,g=h,d={}):(d=f[p]=f[p]||{},g=r);for(_ in g)m=h&&h[_],m&&((!("kill"in m.d)||m.d.kill(_)===!0)&&yl(this,m,"_pt"),delete h[_]),d!=="all"&&(d[_]=1)}return this._initted&&!this._pt&&u&&Qr(this),this},e.to=function(s,r){return new e(s,r,arguments[2])},e.from=function(s,r){return fo(1,arguments)},e.delayedCall=function(s,r,o,a){return new e(r,0,{immediateRender:!1,lazy:!1,overwrite:!1,delay:s,onComplete:r,onReverseComplete:r,onCompleteParams:o,onReverseCompleteParams:o,callbackScope:a})},e.fromTo=function(s,r,o){return fo(2,arguments)},e.set=function(s,r){return r.duration=0,r.repeatDelay||(r.repeat=0),new e(s,r)},e.killTweensOf=function(s,r,o){return xt.killTweensOf(s,r,o)},e}(wo);Rn(Pt.prototype,{_targets:[],_lazy:0,_startAt:0,_op:0,_onInit:0});hn("staggerTo,staggerFrom,staggerFromTo",function(i){Pt[i]=function(){var e=new cn,t=Jc.call(arguments,0);return t.splice(i==="staggerFromTo"?5:4,0,0),e[i].apply(e,t)}});var Gu=function(e,t,n){return e[t]=n},Jm=function(e,t,n){return e[t](n)},sT=function(e,t,n,s){return e[t](s.fp,n)},rT=function(e,t,n){return e.setAttribute(t,n)},Wu=function(e,t){return Et(e[t])?Jm:Uu(e[t])&&e.setAttribute?rT:Gu},Qm=function(e,t){return t.set(t.t,t.p,Math.round((t.s+t.c*e)*1e6)/1e6,t)},oT=function(e,t){return t.set(t.t,t.p,!!(t.s+t.c*e),t)},e_=function(e,t){var n=t._pt,s="";if(!e&&t.b)s=t.b;else if(e===1&&t.e)s=t.e;else{for(;n;)s=n.p+(n.m?n.m(n.s+n.c*e):Math.round((n.s+n.c*e)*1e4)/1e4)+s,n=n._next;s+=t.c}t.set(t.t,t.p,s,t)},Xu=function(e,t){for(var n=t._pt;n;)n.r(e,n.d),n=n._next},aT=function(e,t,n,s){for(var r=this._pt,o;r;)o=r._next,r.p===s&&r.modifier(e,t,n),r=o},lT=function(e){for(var t=this._pt,n,s;t;)s=t._next,t.p===e&&!t.op||t.op===e?yl(this,t,"_pt"):t.dep||(n=1),t=s;return!n},cT=function(e,t,n,s){s.mSet(e,t,s.m.call(s.tween,n,s.mt),s)},t_=function(e){for(var t=e._pt,n,s,r,o;t;){for(n=t._next,s=r;s&&s.pr>t.pr;)s=s._next;(t._prev=s?s._prev:o)?t._prev._next=t:r=t,(t._next=s)?s._prev=t:o=t,t=n}e._pt=r},dn=function(){function i(t,n,s,r,o,a,l,c,u){this.t=n,this.s=r,this.c=o,this.p=s,this.r=a||Qm,this.d=l||this,this.set=c||Gu,this.pr=u||0,this._next=t,t&&(t._prev=this)}var e=i.prototype;return e.modifier=function(n,s,r){this.mSet=this.mSet||this.set,this.set=cT,this.m=n,this.mt=r,this.tween=s},i}();hn(zu+"parent,duration,ease,delay,overwrite,runBackwards,startAt,yoyo,immediateRender,repeat,repeatDelay,data,paused,reversed,lazy,callbackScope,stringFilter,id,yoyoEase,stagger,inherit,repeatRefresh,keyframes,autoRevert,scrollTrigger,easeReverse",function(i){return Fu[i]=1});wn.TweenMax=wn.TweenLite=Pt;wn.TimelineLite=wn.TimelineMax=cn;xt=new cn({sortChildren:!1,defaults:Mo,autoRemoveChildren:!0,id:"root",smoothChildTiming:!0});An.stringFilter=qm;var zs=[],Pa={},uT=[],xd=0,fT=0,yc=function(e){return(Pa[e]||uT).map(function(t){return t()})},nu=function(){var e=Date.now(),t=[];e-xd>2&&(yc("matchMediaInit"),zs.forEach(function(n){var s=n.queries,r=n.conditions,o,a,l,c;for(a in s)o=Jn.matchMedia(s[a]).matches,o&&(l=1),o!==r[a]&&(r[a]=o,c=1);c&&(n.revert(),l&&t.push(n))}),yc("matchMediaRevert"),t.forEach(function(n){return n.onMatch(n,function(s){return n.add(null,s)})}),xd=e,yc("matchMedia"))},n_=function(){function i(t,n){this.selector=n&&Qc(n),this.data=[],this._r=[],this.isReverted=!1,this.id=fT++,t&&this.add(t)}var e=i.prototype;return e.add=function(n,s,r){Et(n)&&(r=s,s=n,n=Et);var o=this,a=function(){var c=_t,u=o.selector,f;return c&&c!==o&&c.data.push(o),r&&(o.selector=Qc(r)),_t=o,f=s.apply(o,arguments),Et(f)&&o._r.push(f),_t=c,o.selector=u,o.isReverted=!1,f};return o.last=a,n===Et?a(o,function(l){return o.add(null,l)}):n?o[n]=a:a},e.ignore=function(n){var s=_t;_t=null,n(this),_t=s},e.getTweens=function(){var n=[];return this.data.forEach(function(s){return s instanceof i?n.push.apply(n,s.getTweens()):s instanceof Pt&&!(s.parent&&s.parent.data==="nested")&&n.push(s)}),n},e.clear=function(){this._r.length=this.data.length=0},e.kill=function(n,s){var r=this;if(n?function(){for(var a=r.getTweens(),l=r.data.length,c;l--;)c=r.data[l],c.data==="isFlip"&&(c.revert(),c.getChildren(!0,!0,!1).forEach(function(u){return a.splice(a.indexOf(u),1)}));for(a.map(function(u){return{g:u._dur||u._delay||u._sat&&!u._sat.vars.immediateRender?u.globalTime(0):-1/0,t:u}}).sort(function(u,f){return f.g-u.g||-1/0}).forEach(function(u){return u.t.revert(n)}),l=r.data.length;l--;)c=r.data[l],c instanceof cn?c.data!=="nested"&&(c.scrollTrigger&&c.scrollTrigger.revert(),c.kill()):!(c instanceof Pt)&&c.revert&&c.revert(n);r._r.forEach(function(u){return u(n,r)}),r.isReverted=!0}():this.data.forEach(function(a){return a.kill&&a.kill()}),this.clear(),s)for(var o=zs.length;o--;)zs[o].id===this.id&&zs.splice(o,1)},e.revert=function(n){this.kill(n||{})},i}(),hT=function(){function i(t){this.contexts=[],this.scope=t,_t&&_t.data.push(this)}var e=i.prototype;return e.add=function(n,s,r){li(n)||(n={matches:n});var o=new n_(0,r||this.scope),a=o.conditions={},l,c,u;_t&&!o.selector&&(o.selector=_t.selector),this.contexts.push(o),s=o.add("onMatch",s),o.queries=n;for(c in n)c==="all"?u=1:(l=Jn.matchMedia(n[c]),l&&(zs.indexOf(o)<0&&zs.push(o),(a[c]=l.matches)&&(u=1),l.addListener?l.addListener(nu):l.addEventListener("change",nu)));return u&&s(o,function(f){return o.add(null,f)}),this},e.revert=function(n){this.kill(n||{})},e.kill=function(n){this.contexts.forEach(function(s){return s.kill(n,!0)})},i}(),Za={registerPlugin:function(){for(var e=arguments.length,t=new Array(e),n=0;n<e;n++)t[n]=arguments[n];t.forEach(function(s){return Gm(s)})},timeline:function(e){return new cn(e)},getTweensOf:function(e,t){return xt.getTweensOf(e,t)},getProperty:function(e,t,n,s){zt(e)&&(e=Fn(e)[0]);var r=Os(e||{}).get,o=n?Pm:Cm;return n==="native"&&(n=""),e&&(t?o((xn[t]&&xn[t].get||r)(e,t,n,s)):function(a,l,c){return o((xn[a]&&xn[a].get||r)(e,a,l,c))})},quickSetter:function(e,t,n){if(e=Fn(e),e.length>1){var s=e.map(function(u){return mn.quickSetter(u,t,n)}),r=s.length;return function(u){for(var f=r;f--;)s[f](u)}}e=e[0]||{};var o=xn[t],a=Os(e),l=a.harness&&(a.harness.aliases||{})[t]||t,c=o?function(u){var f=new o;pr._pt=0,f.init(e,n?u+n:u,pr,0,[e]),f.render(1,f),pr._pt&&Xu(1,pr)}:a.set(e,l);return o?c:function(u){return c(e,l,n?u+n:u,a,1)}},quickTo:function(e,t,n){var s,r=mn.to(e,Rn((s={},s[t]="+=0.1",s.paused=!0,s.stagger=0,s),n||{})),o=function(l,c,u){return r.resetTo(t,l,c,u)};return o.tween=r,o},isTweening:function(e){return xt.getTweensOf(e,!0).length>0},defaults:function(e){return e&&e.ease&&(e.ease=Fs(e.ease,Mo.ease)),pd(Mo,e||{})},config:function(e){return pd(An,e||{})},registerEffect:function(e){var t=e.name,n=e.effect,s=e.plugins,r=e.defaults,o=e.extendTimeline;(s||"").split(",").forEach(function(a){return a&&!xn[a]&&!wn[a]&&Eo(t+" effect requires "+a+" plugin.")}),_c[t]=function(a,l,c){return n(Fn(a),Rn(l||{},r),c)},o&&(cn.prototype[t]=function(a,l,c){return this.add(_c[t](a,li(l)?l:(c=l)&&{},this),c)})},registerEase:function(e,t){et[e]=Fs(t)},parseEase:function(e,t){return arguments.length?Fs(e,t):et},getById:function(e){return xt.getById(e)},exportRoot:function(e,t){e===void 0&&(e={});var n=new cn(e),s,r;for(n.smoothChildTiming=fn(e.smoothChildTiming),xt.remove(n),n._dp=0,n._time=n._tTime=xt._time,s=xt._first;s;)r=s._next,(t||!(!s._dur&&s instanceof Pt&&s.vars.onComplete===s._targets[0]))&&ii(n,s,s._start-s._delay),s=r;return ii(xt,n,0),n},context:function(e,t){return e?new n_(e,t):_t},matchMedia:function(e){return new hT(e)},matchMediaRefresh:function(){return zs.forEach(function(e){var t=e.conditions,n,s;for(s in t)t[s]&&(t[s]=!1,n=1);n&&e.revert()})||nu()},addEventListener:function(e,t){var n=Pa[e]||(Pa[e]=[]);~n.indexOf(t)||n.push(t)},removeEventListener:function(e,t){var n=Pa[e],s=n&&n.indexOf(t);s>=0&&n.splice(s,1)},utils:{wrap:Gb,wrapYoyo:Wb,distribute:Fm,random:Bm,snap:zm,normalize:Hb,getUnit:Yt,clamp:zb,splitColor:Wm,toArray:Fn,selector:Qc,mapRange:Vm,pipe:kb,unitize:Vb,interpolate:Xb,shuffle:Nm},install:bm,effects:_c,ticker:yn,updateRoot:cn.updateRoot,plugins:xn,globalTimeline:xt,core:{PropTween:dn,globals:Tm,Tween:Pt,Timeline:cn,Animation:wo,getCache:Os,_removeLinkedListItem:yl,reverting:function(){return Ht},context:function(e){return e&&_t&&(_t.data.push(e),e._ctx=_t),_t},suppressOverwrites:function(e){return Du=e}}};hn("to,from,fromTo,delayedCall,set,killTweensOf",function(i){return Za[i]=Pt[i]});yn.add(cn.updateRoot);pr=Za.to({},{duration:0});var dT=function(e,t){for(var n=e._pt;n&&n.p!==t&&n.op!==t&&n.fp!==t;)n=n._next;return n},pT=function(e,t){var n=e._targets,s,r,o;for(s in t)for(r=n.length;r--;)o=e._ptLookup[r][s],o&&(o=o.d)&&(o._pt&&(o=dT(o,s)),o&&o.modifier&&o.modifier(t[s],e,n[r],s))},Sc=function(e,t){return{name:e,headless:1,rawVars:1,init:function(s,r,o){o._onInit=function(a){var l,c;if(zt(r)&&(l={},hn(r,function(u){return l[u]=1}),r=l),t){l={};for(c in r)l[c]=t(r[c]);r=l}pT(a,r)}}}},mn=Za.registerPlugin({name:"attr",init:function(e,t,n,s,r){var o,a,l;this.tween=n;for(o in t)l=e.getAttribute(o)||"",a=this.add(e,"setAttribute",(l||0)+"",t[o],s,r,0,0,o),a.op=o,a.b=l,this._props.push(o)},render:function(e,t){for(var n=t._pt;n;)Ht?n.set(n.t,n.p,n.b,n):n.r(e,n.d),n=n._next}},{name:"endArray",headless:1,init:function(e,t){for(var n=t.length;n--;)this.add(e,n,e[n]||0,t[n],0,0,0,0,0,1)}},Sc("roundProps",eu),Sc("modifiers"),Sc("snap",zm))||Za;Pt.version=cn.version=mn.version="3.15.0";Em=1;Iu()&&Or();et.Power0;et.Power1;et.Power2;et.Power3;et.Power4;et.Linear;et.Quad;et.Cubic;et.Quart;et.Quint;et.Strong;et.Elastic;et.Back;et.SteppedEase;et.Bounce;et.Sine;et.Expo;et.Circ;/*!
 * CSSPlugin 3.15.0
 * https://gsap.com
 *
 * Copyright 2008-2026, GreenSock. All rights reserved.
 * Subject to the terms at https://gsap.com/standard-license
 * @author: Jack Doyle, jack@greensock.com
*/var yd,ji,br,qu,Rs,Sd,Yu,mT=function(){return typeof window<"u"},Ii={},Es=180/Math.PI,Tr=Math.PI/180,cr=Math.atan2,Md=1e8,$u=/([A-Z])/g,_T=/(left|right|width|margin|padding|x)/i,gT=/[\s,\(]\S/,si={autoAlpha:"opacity,visibility",scale:"scaleX,scaleY",alpha:"opacity"},iu=function(e,t){return t.set(t.t,t.p,Math.round((t.s+t.c*e)*1e4)/1e4+t.u,t)},vT=function(e,t){return t.set(t.t,t.p,e===1?t.e:Math.round((t.s+t.c*e)*1e4)/1e4+t.u,t)},xT=function(e,t){return t.set(t.t,t.p,e?Math.round((t.s+t.c*e)*1e4)/1e4+t.u:t.b,t)},yT=function(e,t){return t.set(t.t,t.p,e===1?t.e:e?Math.round((t.s+t.c*e)*1e4)/1e4+t.u:t.b,t)},ST=function(e,t){var n=t.s+t.c*e;t.set(t.t,t.p,~~(n+(n<0?-.5:.5))+t.u,t)},i_=function(e,t){return t.set(t.t,t.p,e?t.e:t.b,t)},s_=function(e,t){return t.set(t.t,t.p,e!==1?t.b:t.e,t)},MT=function(e,t,n){return e.style[t]=n},ET=function(e,t,n){return e.style.setProperty(t,n)},bT=function(e,t,n){return e._gsap[t]=n},TT=function(e,t,n){return e._gsap.scaleX=e._gsap.scaleY=n},AT=function(e,t,n,s,r){var o=e._gsap;o.scaleX=o.scaleY=n,o.renderTransform(r,o)},wT=function(e,t,n,s,r){var o=e._gsap;o[t]=n,o.renderTransform(r,o)},yt="transform",pn=yt+"Origin",RT=function i(e,t){var n=this,s=this.target,r=s.style,o=s._gsap;if(e in Ii&&r){if(this.tfm=this.tfm||{},e!=="transform")e=si[e]||e,~e.indexOf(",")?e.split(",").forEach(function(a){return n.tfm[a]=Mi(s,a)}):this.tfm[e]=o.x?o[e]:Mi(s,e),e===pn&&(this.tfm.zOrigin=o.zOrigin);else return si.transform.split(",").forEach(function(a){return i.call(n,a,t)});if(this.props.indexOf(yt)>=0)return;o.svg&&(this.svgo=s.getAttribute("data-svg-origin"),this.props.push(pn,t,"")),e=yt}(r||t)&&this.props.push(e,t,r[e])},r_=function(e){e.translate&&(e.removeProperty("translate"),e.removeProperty("scale"),e.removeProperty("rotate"))},CT=function(){var e=this.props,t=this.target,n=t.style,s=t._gsap,r,o;for(r=0;r<e.length;r+=3)e[r+1]?e[r+1]===2?t[e[r]](e[r+2]):t[e[r]]=e[r+2]:e[r+2]?n[e[r]]=e[r+2]:n.removeProperty(e[r].substr(0,2)==="--"?e[r]:e[r].replace($u,"-$1").toLowerCase());if(this.tfm){for(o in this.tfm)s[o]=this.tfm[o];s.svg&&(s.renderTransform(),t.setAttribute("data-svg-origin",this.svgo||"")),r=Yu(),(!r||!r.isStart)&&!n[yt]&&(r_(n),s.zOrigin&&n[pn]&&(n[pn]+=" "+s.zOrigin+"px",s.zOrigin=0,s.renderTransform()),s.uncache=1)}},o_=function(e,t){var n={target:e,props:[],revert:CT,save:RT};return e._gsap||mn.core.getCache(e),t&&e.style&&e.nodeType&&t.split(",").forEach(function(s){return n.save(s)}),n},a_,su=function(e,t){var n=ji.createElementNS?ji.createElementNS((t||"http://www.w3.org/1999/xhtml").replace(/^https/,"http"),e):ji.createElement(e);return n&&n.style?n:ji.createElement(e)},En=function i(e,t,n){var s=getComputedStyle(e);return s[t]||s.getPropertyValue(t.replace($u,"-$1").toLowerCase())||s.getPropertyValue(t)||!n&&i(e,Nr(t)||t,1)||""},Ed="O,Moz,ms,Ms,Webkit".split(","),Nr=function(e,t,n){var s=t||Rs,r=s.style,o=5;if(e in r&&!n)return e;for(e=e.charAt(0).toUpperCase()+e.substr(1);o--&&!(Ed[o]+e in r););return o<0?null:(o===3?"ms":o>=0?Ed[o]:"")+e},ru=function(){mT()&&window.document&&(yd=window,ji=yd.document,br=ji.documentElement,Rs=su("div")||{style:{}},su("div"),yt=Nr(yt),pn=yt+"Origin",Rs.style.cssText="border-width:0;line-height:0;position:absolute;padding:0",a_=!!Nr("perspective"),Yu=mn.core.reverting,qu=1)},bd=function(e){var t=e.ownerSVGElement,n=su("svg",t&&t.getAttribute("xmlns")||"http://www.w3.org/2000/svg"),s=e.cloneNode(!0),r;s.style.display="block",n.appendChild(s),br.appendChild(n);try{r=s.getBBox()}catch{}return n.removeChild(s),br.removeChild(n),r},Td=function(e,t){for(var n=t.length;n--;)if(e.hasAttribute(t[n]))return e.getAttribute(t[n])},l_=function(e){var t,n;try{t=e.getBBox()}catch{t=bd(e),n=1}return t&&(t.width||t.height)||n||(t=bd(e)),t&&!t.width&&!t.x&&!t.y?{x:+Td(e,["x","cx","x1"])||0,y:+Td(e,["y","cy","y1"])||0,width:0,height:0}:t},c_=function(e){return!!(e.getCTM&&(!e.parentNode||e.ownerSVGElement)&&l_(e))},as=function(e,t){if(t){var n=e.style,s;t in Ii&&t!==pn&&(t=yt),n.removeProperty?(s=t.substr(0,2),(s==="ms"||t.substr(0,6)==="webkit")&&(t="-"+t),n.removeProperty(s==="--"?t:t.replace($u,"-$1").toLowerCase())):n.removeAttribute(t)}},Ki=function(e,t,n,s,r,o){var a=new dn(e._pt,t,n,0,1,o?s_:i_);return e._pt=a,a.b=s,a.e=r,e._props.push(n),a},Ad={deg:1,rad:1,turn:1},PT={grid:1,flex:1},ls=function i(e,t,n,s){var r=parseFloat(n)||0,o=(n+"").trim().substr((r+"").length)||"px",a=Rs.style,l=_T.test(t),c=e.tagName.toLowerCase()==="svg",u=(c?"client":"offset")+(l?"Width":"Height"),f=100,h=s==="px",d=s==="%",g,_,m,p;if(s===o||!r||Ad[s]||Ad[o])return r;if(o!=="px"&&!h&&(r=i(e,t,n,"px")),p=e.getCTM&&c_(e),(d||o==="%")&&(Ii[t]||~t.indexOf("adius")))return g=p?e.getBBox()[l?"width":"height"]:e[u],wt(d?r/g*f:r/100*g);if(a[l?"width":"height"]=f+(h?o:s),_=s!=="rem"&&~t.indexOf("adius")||s==="em"&&e.appendChild&&!c?e:e.parentNode,p&&(_=(e.ownerSVGElement||{}).parentNode),(!_||_===ji||!_.appendChild)&&(_=ji.body),m=_._gsap,m&&d&&m.width&&l&&m.time===yn.time&&!m.uncache)return wt(r/m.width*f);if(d&&(t==="height"||t==="width")){var x=e.style[t];e.style[t]=f+s,g=e[u],x?e.style[t]=x:as(e,t)}else(d||o==="%")&&!PT[En(_,"display")]&&(a.position=En(e,"position")),_===e&&(a.position="static"),_.appendChild(Rs),g=Rs[u],_.removeChild(Rs),a.position="absolute";return l&&d&&(m=Os(_),m.time=yn.time,m.width=_[u]),wt(h?g*r/f:g&&r?f/g*r:0)},Mi=function(e,t,n,s){var r;return qu||ru(),t in si&&t!=="transform"&&(t=si[t],~t.indexOf(",")&&(t=t.split(",")[0])),Ii[t]&&t!=="transform"?(r=Co(e,s),r=t!=="transformOrigin"?r[t]:r.svg?r.origin:Qa(En(e,pn))+" "+r.zOrigin+"px"):(r=e.style[t],(!r||r==="auto"||s||~(r+"").indexOf("calc("))&&(r=Ja[t]&&Ja[t](e,t,n)||En(e,t)||wm(e,t)||(t==="opacity"?1:0))),n&&!~(r+"").trim().indexOf(" ")?ls(e,t,r,n)+n:r},LT=function(e,t,n,s){if(!n||n==="none"){var r=Nr(t,e,1),o=r&&En(e,r,1);o&&o!==n?(t=r,n=o):t==="borderColor"&&(n=En(e,"borderTopColor"))}var a=new dn(this._pt,e.style,t,0,1,e_),l=0,c=0,u,f,h,d,g,_,m,p,x,y,S,R;if(a.b=n,a.e=s,n+="",s+="",s.substring(0,6)==="var(--"&&(s=En(e,s.substring(4,s.indexOf(")")))),s==="auto"&&(_=e.style[t],e.style[t]=s,s=En(e,t)||s,_?e.style[t]=_:as(e,t)),u=[n,s],qm(u),n=u[0],s=u[1],h=n.match(dr)||[],R=s.match(dr)||[],R.length){for(;f=dr.exec(s);)m=f[0],x=s.substring(l,f.index),g?g=(g+1)%5:(x.substr(-5)==="rgba("||x.substr(-5)==="hsla(")&&(g=1),m!==(_=h[c++]||"")&&(d=parseFloat(_)||0,S=_.substr((d+"").length),m.charAt(1)==="="&&(m=Er(d,m)+S),p=parseFloat(m),y=m.substr((p+"").length),l=dr.lastIndex-y.length,y||(y=y||An.units[t]||S,l===s.length&&(s+=y,a.e+=y)),S!==y&&(d=ls(e,t,_,y)||0),a._pt={_next:a._pt,p:x||c===1?x:",",s:d,c:p-d,m:g&&g<4||t==="zIndex"?Math.round:0});a.c=l<s.length?s.substring(l,s.length):""}else a.r=t==="display"&&s==="none"?s_:i_;return Mm.test(s)&&(a.e=0),this._pt=a,a},wd={top:"0%",bottom:"100%",left:"0%",right:"100%",center:"50%"},DT=function(e){var t=e.split(" "),n=t[0],s=t[1]||"50%";return(n==="top"||n==="bottom"||s==="left"||s==="right")&&(e=n,n=s,s=e),t[0]=wd[n]||n,t[1]=wd[s]||s,t.join(" ")},UT=function(e,t){if(t.tween&&t.tween._time===t.tween._dur){var n=t.t,s=n.style,r=t.u,o=n._gsap,a,l,c;if(r==="all"||r===!0)s.cssText="",l=1;else for(r=r.split(","),c=r.length;--c>-1;)a=r[c],Ii[a]&&(l=1,a=a==="transformOrigin"?pn:yt),as(n,a);l&&(as(n,yt),o&&(o.svg&&n.removeAttribute("transform"),s.scale=s.rotate=s.translate="none",Co(n,1),o.uncache=1,r_(s)))}},Ja={clearProps:function(e,t,n,s,r){if(r.data!=="isFromStart"){var o=e._pt=new dn(e._pt,t,n,0,0,UT);return o.u=s,o.pr=-10,o.tween=r,e._props.push(n),1}}},Ro=[1,0,0,1,0,0],u_={},f_=function(e){return e==="matrix(1, 0, 0, 1, 0, 0)"||e==="none"||!e},Rd=function(e){var t=En(e,yt);return f_(t)?Ro:t.substr(7).match(Sm).map(wt)},ju=function(e,t){var n=e._gsap||Os(e),s=e.style,r=Rd(e),o,a,l,c;return n.svg&&e.getAttribute("transform")?(l=e.transform.baseVal.consolidate().matrix,r=[l.a,l.b,l.c,l.d,l.e,l.f],r.join(",")==="1,0,0,1,0,0"?Ro:r):(r===Ro&&!e.offsetParent&&e!==br&&!n.svg&&(l=s.display,s.display="block",o=e.parentNode,(!o||!e.offsetParent&&!e.getBoundingClientRect().width)&&(c=1,a=e.nextElementSibling,br.appendChild(e)),r=Rd(e),l?s.display=l:as(e,"display"),c&&(a?o.insertBefore(e,a):o?o.appendChild(e):br.removeChild(e))),t&&r.length>6?[r[0],r[1],r[4],r[5],r[12],r[13]]:r)},ou=function(e,t,n,s,r,o){var a=e._gsap,l=r||ju(e,!0),c=a.xOrigin||0,u=a.yOrigin||0,f=a.xOffset||0,h=a.yOffset||0,d=l[0],g=l[1],_=l[2],m=l[3],p=l[4],x=l[5],y=t.split(" "),S=parseFloat(y[0])||0,R=parseFloat(y[1])||0,L,w,B,v;n?l!==Ro&&(w=d*m-g*_)&&(B=S*(m/w)+R*(-_/w)+(_*x-m*p)/w,v=S*(-g/w)+R*(d/w)-(d*x-g*p)/w,S=B,R=v):(L=l_(e),S=L.x+(~y[0].indexOf("%")?S/100*L.width:S),R=L.y+(~(y[1]||y[0]).indexOf("%")?R/100*L.height:R)),s||s!==!1&&a.smooth?(p=S-c,x=R-u,a.xOffset=f+(p*d+x*_)-p,a.yOffset=h+(p*g+x*m)-x):a.xOffset=a.yOffset=0,a.xOrigin=S,a.yOrigin=R,a.smooth=!!s,a.origin=t,a.originIsAbsolute=!!n,e.style[pn]="0px 0px",o&&(Ki(o,a,"xOrigin",c,S),Ki(o,a,"yOrigin",u,R),Ki(o,a,"xOffset",f,a.xOffset),Ki(o,a,"yOffset",h,a.yOffset)),e.setAttribute("data-svg-origin",S+" "+R)},Co=function(e,t){var n=e._gsap||new $m(e);if("x"in n&&!t&&!n.uncache)return n;var s=e.style,r=n.scaleX<0,o="px",a="deg",l=getComputedStyle(e),c=En(e,pn)||"0",u,f,h,d,g,_,m,p,x,y,S,R,L,w,B,v,b,N,A,I,O,k,H,q,Z,W,j,G,re,Q,le,_e;return u=f=h=_=m=p=x=y=S=0,d=g=1,n.svg=!!(e.getCTM&&c_(e)),l.translate&&((l.translate!=="none"||l.scale!=="none"||l.rotate!=="none")&&(s[yt]=(l.translate!=="none"?"translate3d("+(l.translate+" 0 0").split(" ").slice(0,3).join(", ")+") ":"")+(l.rotate!=="none"?"rotate("+l.rotate+") ":"")+(l.scale!=="none"?"scale("+l.scale.split(" ").join(",")+") ":"")+(l[yt]!=="none"?l[yt]:"")),s.scale=s.rotate=s.translate="none"),w=ju(e,n.svg),n.svg&&(n.uncache?(Z=e.getBBox(),c=n.xOrigin-Z.x+"px "+(n.yOrigin-Z.y)+"px",q=""):q=!t&&e.getAttribute("data-svg-origin"),ou(e,q||c,!!q||n.originIsAbsolute,n.smooth!==!1,w)),R=n.xOrigin||0,L=n.yOrigin||0,w!==Ro&&(N=w[0],A=w[1],I=w[2],O=w[3],u=k=w[4],f=H=w[5],w.length===6?(d=Math.sqrt(N*N+A*A),g=Math.sqrt(O*O+I*I),_=N||A?cr(A,N)*Es:0,x=I||O?cr(I,O)*Es+_:0,x&&(g*=Math.abs(Math.cos(x*Tr))),n.svg&&(u-=R-(R*N+L*I),f-=L-(R*A+L*O))):(_e=w[6],Q=w[7],j=w[8],G=w[9],re=w[10],le=w[11],u=w[12],f=w[13],h=w[14],B=cr(_e,re),m=B*Es,B&&(v=Math.cos(-B),b=Math.sin(-B),q=k*v+j*b,Z=H*v+G*b,W=_e*v+re*b,j=k*-b+j*v,G=H*-b+G*v,re=_e*-b+re*v,le=Q*-b+le*v,k=q,H=Z,_e=W),B=cr(-I,re),p=B*Es,B&&(v=Math.cos(-B),b=Math.sin(-B),q=N*v-j*b,Z=A*v-G*b,W=I*v-re*b,le=O*b+le*v,N=q,A=Z,I=W),B=cr(A,N),_=B*Es,B&&(v=Math.cos(B),b=Math.sin(B),q=N*v+A*b,Z=k*v+H*b,A=A*v-N*b,H=H*v-k*b,N=q,k=Z),m&&Math.abs(m)+Math.abs(_)>359.9&&(m=_=0,p=180-p),d=wt(Math.sqrt(N*N+A*A+I*I)),g=wt(Math.sqrt(H*H+_e*_e)),B=cr(k,H),x=Math.abs(B)>2e-4?B*Es:0,S=le?1/(le<0?-le:le):0),n.svg&&(q=e.getAttribute("transform"),n.forceCSS=e.setAttribute("transform","")||!f_(En(e,yt)),q&&e.setAttribute("transform",q))),Math.abs(x)>90&&Math.abs(x)<270&&(r?(d*=-1,x+=_<=0?180:-180,_+=_<=0?180:-180):(g*=-1,x+=x<=0?180:-180)),t=t||n.uncache,n.x=u-((n.xPercent=u&&(!t&&n.xPercent||(Math.round(e.offsetWidth/2)===Math.round(-u)?-50:0)))?e.offsetWidth*n.xPercent/100:0)+o,n.y=f-((n.yPercent=f&&(!t&&n.yPercent||(Math.round(e.offsetHeight/2)===Math.round(-f)?-50:0)))?e.offsetHeight*n.yPercent/100:0)+o,n.z=h+o,n.scaleX=wt(d),n.scaleY=wt(g),n.rotation=wt(_)+a,n.rotationX=wt(m)+a,n.rotationY=wt(p)+a,n.skewX=x+a,n.skewY=y+a,n.transformPerspective=S+o,(n.zOrigin=parseFloat(c.split(" ")[2])||!t&&n.zOrigin||0)&&(s[pn]=Qa(c)),n.xOffset=n.yOffset=0,n.force3D=An.force3D,n.renderTransform=n.svg?OT:a_?h_:IT,n.uncache=0,n},Qa=function(e){return(e=e.split(" "))[0]+" "+e[1]},Mc=function(e,t,n){var s=Yt(t);return wt(parseFloat(t)+parseFloat(ls(e,"x",n+"px",s)))+s},IT=function(e,t){t.z="0px",t.rotationY=t.rotationX="0deg",t.force3D=0,h_(e,t)},xs="0deg",jr="0px",ys=") ",h_=function(e,t){var n=t||this,s=n.xPercent,r=n.yPercent,o=n.x,a=n.y,l=n.z,c=n.rotation,u=n.rotationY,f=n.rotationX,h=n.skewX,d=n.skewY,g=n.scaleX,_=n.scaleY,m=n.transformPerspective,p=n.force3D,x=n.target,y=n.zOrigin,S="",R=p==="auto"&&e&&e!==1||p===!0;if(y&&(f!==xs||u!==xs)){var L=parseFloat(u)*Tr,w=Math.sin(L),B=Math.cos(L),v;L=parseFloat(f)*Tr,v=Math.cos(L),o=Mc(x,o,w*v*-y),a=Mc(x,a,-Math.sin(L)*-y),l=Mc(x,l,B*v*-y+y)}m!==jr&&(S+="perspective("+m+ys),(s||r)&&(S+="translate("+s+"%, "+r+"%) "),(R||o!==jr||a!==jr||l!==jr)&&(S+=l!==jr||R?"translate3d("+o+", "+a+", "+l+") ":"translate("+o+", "+a+ys),c!==xs&&(S+="rotate("+c+ys),u!==xs&&(S+="rotateY("+u+ys),f!==xs&&(S+="rotateX("+f+ys),(h!==xs||d!==xs)&&(S+="skew("+h+", "+d+ys),(g!==1||_!==1)&&(S+="scale("+g+", "+_+ys),x.style[yt]=S||"translate(0, 0)"},OT=function(e,t){var n=t||this,s=n.xPercent,r=n.yPercent,o=n.x,a=n.y,l=n.rotation,c=n.skewX,u=n.skewY,f=n.scaleX,h=n.scaleY,d=n.target,g=n.xOrigin,_=n.yOrigin,m=n.xOffset,p=n.yOffset,x=n.forceCSS,y=parseFloat(o),S=parseFloat(a),R,L,w,B,v;l=parseFloat(l),c=parseFloat(c),u=parseFloat(u),u&&(u=parseFloat(u),c+=u,l+=u),l||c?(l*=Tr,c*=Tr,R=Math.cos(l)*f,L=Math.sin(l)*f,w=Math.sin(l-c)*-h,B=Math.cos(l-c)*h,c&&(u*=Tr,v=Math.tan(c-u),v=Math.sqrt(1+v*v),w*=v,B*=v,u&&(v=Math.tan(u),v=Math.sqrt(1+v*v),R*=v,L*=v)),R=wt(R),L=wt(L),w=wt(w),B=wt(B)):(R=f,B=h,L=w=0),(y&&!~(o+"").indexOf("px")||S&&!~(a+"").indexOf("px"))&&(y=ls(d,"x",o,"px"),S=ls(d,"y",a,"px")),(g||_||m||p)&&(y=wt(y+g-(g*R+_*w)+m),S=wt(S+_-(g*L+_*B)+p)),(s||r)&&(v=d.getBBox(),y=wt(y+s/100*v.width),S=wt(S+r/100*v.height)),v="matrix("+R+","+L+","+w+","+B+","+y+","+S+")",d.setAttribute("transform",v),x&&(d.style[yt]=v)},NT=function(e,t,n,s,r){var o=360,a=zt(r),l=parseFloat(r)*(a&&~r.indexOf("rad")?Es:1),c=l-s,u=s+c+"deg",f,h;return a&&(f=r.split("_")[1],f==="short"&&(c%=o,c!==c%(o/2)&&(c+=c<0?o:-o)),f==="cw"&&c<0?c=(c+o*Md)%o-~~(c/o)*o:f==="ccw"&&c>0&&(c=(c-o*Md)%o-~~(c/o)*o)),e._pt=h=new dn(e._pt,t,n,s,c,vT),h.e=u,h.u="deg",e._props.push(n),h},Cd=function(e,t){for(var n in t)e[n]=t[n];return e},FT=function(e,t,n){var s=Cd({},n._gsap),r="perspective,force3D,transformOrigin,svgOrigin",o=n.style,a,l,c,u,f,h,d,g;s.svg?(c=n.getAttribute("transform"),n.setAttribute("transform",""),o[yt]=t,a=Co(n,1),as(n,yt),n.setAttribute("transform",c)):(c=getComputedStyle(n)[yt],o[yt]=t,a=Co(n,1),o[yt]=c);for(l in Ii)c=s[l],u=a[l],c!==u&&r.indexOf(l)<0&&(d=Yt(c),g=Yt(u),f=d!==g?ls(n,l,c,g):parseFloat(c),h=parseFloat(u),e._pt=new dn(e._pt,a,l,f,h-f,iu),e._pt.u=g||0,e._props.push(l));Cd(a,s)};hn("padding,margin,Width,Radius",function(i,e){var t="Top",n="Right",s="Bottom",r="Left",o=(e<3?[t,n,s,r]:[t+r,t+n,s+n,s+r]).map(function(a){return e<2?i+a:"border"+a+i});Ja[e>1?"border"+i:i]=function(a,l,c,u,f){var h,d;if(arguments.length<4)return h=o.map(function(g){return Mi(a,g,c)}),d=h.join(" "),d.split(h[0]).length===5?h[0]:d;h=(u+"").split(" "),d={},o.forEach(function(g,_){return d[g]=h[_]=h[_]||h[(_-1)/2|0]}),a.init(l,d,f)}});var d_={name:"css",register:ru,targetTest:function(e){return e.style&&e.nodeType},init:function(e,t,n,s,r){var o=this._props,a=e.style,l=n.vars.startAt,c,u,f,h,d,g,_,m,p,x,y,S,R,L,w,B,v;qu||ru(),this.styles=this.styles||o_(e),B=this.styles.props,this.tween=n;for(_ in t)if(_!=="autoRound"&&(u=t[_],!(xn[_]&&jm(_,t,n,s,e,r)))){if(d=typeof u,g=Ja[_],d==="function"&&(u=u.call(n,s,e,r),d=typeof u),d==="string"&&~u.indexOf("random(")&&(u=To(u)),g)g(this,e,_,u,n)&&(w=1);else if(_.substr(0,2)==="--")c=(getComputedStyle(e).getPropertyValue(_)+"").trim(),u+="",ns.lastIndex=0,ns.test(c)||(m=Yt(c),p=Yt(u),p?m!==p&&(c=ls(e,_,c,p)+p):m&&(u+=m)),this.add(a,"setProperty",c,u,s,r,0,0,_),o.push(_),B.push(_,0,a[_]);else if(d!=="undefined"){if(l&&_ in l?(c=typeof l[_]=="function"?l[_].call(n,s,e,r):l[_],zt(c)&&~c.indexOf("random(")&&(c=To(c)),Yt(c+"")||c==="auto"||(c+=An.units[_]||Yt(Mi(e,_))||""),(c+"").charAt(1)==="="&&(c=Mi(e,_))):c=Mi(e,_),h=parseFloat(c),x=d==="string"&&u.charAt(1)==="="&&u.substr(0,2),x&&(u=u.substr(2)),f=parseFloat(u),_ in si&&(_==="autoAlpha"&&(h===1&&Mi(e,"visibility")==="hidden"&&f&&(h=0),B.push("visibility",0,a.visibility),Ki(this,a,"visibility",h?"inherit":"hidden",f?"inherit":"hidden",!f)),_!=="scale"&&_!=="transform"&&(_=si[_],~_.indexOf(",")&&(_=_.split(",")[0]))),y=_ in Ii,y){if(this.styles.save(_),v=u,d==="string"&&u.substring(0,6)==="var(--"){if(u=En(e,u.substring(4,u.indexOf(")"))),u.substring(0,5)==="calc("){var b=e.style.perspective;e.style.perspective=u,u=En(e,"perspective"),b?e.style.perspective=b:as(e,"perspective")}f=parseFloat(u)}if(S||(R=e._gsap,R.renderTransform&&!t.parseTransform||Co(e,t.parseTransform),L=t.smoothOrigin!==!1&&R.smooth,S=this._pt=new dn(this._pt,a,yt,0,1,R.renderTransform,R,0,-1),S.dep=1),_==="scale")this._pt=new dn(this._pt,R,"scaleY",R.scaleY,(x?Er(R.scaleY,x+f):f)-R.scaleY||0,iu),this._pt.u=0,o.push("scaleY",_),_+="X";else if(_==="transformOrigin"){B.push(pn,0,a[pn]),u=DT(u),R.svg?ou(e,u,0,L,0,this):(p=parseFloat(u.split(" ")[2])||0,p!==R.zOrigin&&Ki(this,R,"zOrigin",R.zOrigin,p),Ki(this,a,_,Qa(c),Qa(u)));continue}else if(_==="svgOrigin"){ou(e,u,1,L,0,this);continue}else if(_ in u_){NT(this,R,_,h,x?Er(h,x+u):u);continue}else if(_==="smoothOrigin"){Ki(this,R,"smooth",R.smooth,u);continue}else if(_==="force3D"){R[_]=u;continue}else if(_==="transform"){FT(this,u,e);continue}}else _ in a||(_=Nr(_)||_);if(y||(f||f===0)&&(h||h===0)&&!gT.test(u)&&_ in a)m=(c+"").substr((h+"").length),f||(f=0),p=Yt(u)||(_ in An.units?An.units[_]:m),m!==p&&(h=ls(e,_,c,p)),this._pt=new dn(this._pt,y?R:a,_,h,(x?Er(h,x+f):f)-h,!y&&(p==="px"||_==="zIndex")&&t.autoRound!==!1?ST:iu),this._pt.u=p||0,y&&v!==u?(this._pt.b=c,this._pt.e=v,this._pt.r=yT):m!==p&&p!=="%"&&(this._pt.b=c,this._pt.r=xT);else if(_ in a)LT.call(this,e,_,c,x?x+u:u);else if(_ in e)this.add(e,_,c||e[_],x?x+u:u,s,r);else if(_!=="parseTransform"){Nu(_,u);continue}y||(_ in a?B.push(_,0,a[_]):typeof e[_]=="function"?B.push(_,2,e[_]()):B.push(_,1,c||e[_])),o.push(_)}}w&&t_(this)},render:function(e,t){if(t.tween._time||!Yu())for(var n=t._pt;n;)n.r(e,n.d),n=n._next;else t.styles.revert()},get:Mi,aliases:si,getSetter:function(e,t,n){var s=si[t];return s&&s.indexOf(",")<0&&(t=s),t in Ii&&t!==pn&&(e._gsap.x||Mi(e,"x"))?n&&Sd===n?t==="scale"?TT:bT:(Sd=n||{})&&(t==="scale"?AT:wT):e.style&&!Uu(e.style[t])?MT:~t.indexOf("-")?ET:Wu(e,t)},core:{_removeProperty:as,_getMatrix:ju}};mn.utils.checkPrefix=Nr;mn.core.getStyleSaver=o_;(function(i,e,t,n){var s=hn(i+","+e+","+t,function(r){Ii[r]=1});hn(e,function(r){An.units[r]="deg",u_[r]=1}),si[s[13]]=i+","+e,hn(n,function(r){var o=r.split(":");si[o[1]]=s[o[0]]})})("x,y,z,scale,scaleX,scaleY,xPercent,yPercent","rotation,rotationX,rotationY,skewX,skewY","transform,transformOrigin,svgOrigin,force3D,smoothOrigin,transformPerspective","0:translateX,1:translateY,2:translateZ,8:rotate,8:rotationZ,8:rotateZ,9:rotateX,10:rotateY");hn("x,y,z,top,right,bottom,left,width,height,fontSize,padding,margin,perspective",function(i){An.units[i]="px"});mn.registerPlugin(d_);var Ku=mn.registerPlugin(d_)||mn;Ku.core.Tween;/*!
 * paths 3.15.0
 * https://gsap.com
 *
 * Copyright 2008-2026, GreenSock. All rights reserved.
 * Subject to the terms at https://gsap.com/standard-license
 * @author: Jack Doyle, jack@greensock.com
*/var zT=/[achlmqstvz]|(-?\d*\.?\d*(?:e[\-+]?\d+)?)[0-9]/ig,BT=/[\+\-]?\d*\.?\d+e[\+\-]?\d+/ig,kT=Math.PI/180,xa=Math.sin,ya=Math.cos,po=Math.abs,Kr=Math.sqrt,VT=function(e){return typeof e=="number"},Pd=1e5,Hi=function(e){return Math.round(e*Pd)/Pd||0},Ld=function(e){return e.closed=Math.abs(e[0]-e[e.length-2])<.001&&Math.abs(e[1]-e[e.length-1])<.001};function HT(i,e,t,n,s,r,o){for(var a=i.length,l,c,u,f,h;--a>-1;)for(l=i[a],c=l.length,u=0;u<c;u+=2)f=l[u],h=l[u+1],l[u]=f*e+h*n+r,l[u+1]=f*t+h*s+o;return i._dirty=1,i}function GT(i,e,t,n,s,r,o,a,l){if(!(i===a&&e===l)){t=po(t),n=po(n);var c=s%360*kT,u=ya(c),f=xa(c),h=Math.PI,d=h*2,g=(i-a)/2,_=(e-l)/2,m=u*g+f*_,p=-f*g+u*_,x=m*m,y=p*p,S=x/(t*t)+y/(n*n);S>1&&(t=Kr(S)*t,n=Kr(S)*n);var R=t*t,L=n*n,w=(R*L-R*y-L*x)/(R*y+L*x);w<0&&(w=0);var B=(r===o?-1:1)*Kr(w),v=B*(t*p/n),b=B*-(n*m/t),N=(i+a)/2,A=(e+l)/2,I=N+(u*v-f*b),O=A+(f*v+u*b),k=(m-v)/t,H=(p-b)/n,q=(-m-v)/t,Z=(-p-b)/n,W=k*k+H*H,j=(H<0?-1:1)*Math.acos(k/Kr(W)),G=(k*Z-H*q<0?-1:1)*Math.acos((k*q+H*Z)/Kr(W*(q*q+Z*Z)));isNaN(G)&&(G=h),!o&&G>0?G-=d:o&&G<0&&(G+=d),j%=d,G%=d;var re=Math.ceil(po(G)/(d/4)),Q=[],le=G/re,_e=4/3*xa(le/2)/(1+ya(le/2)),be=u*t,Te=f*t,Ue=f*-n,Ie=u*n,Se;for(Se=0;Se<re;Se++)s=j+Se*le,m=ya(s),p=xa(s),k=ya(s+=le),H=xa(s),Q.push(m-_e*p,p+_e*m,k+_e*H,H-_e*k,k,H);for(Se=0;Se<Q.length;Se+=2)m=Q[Se],p=Q[Se+1],Q[Se]=m*be+p*Ue+I,Q[Se+1]=m*Te+p*Ie+O;return Q[Se-2]=a,Q[Se-1]=l,Q}}function WT(i){var e=(i+"").replace(BT,function(v){var b=+v;return b<1e-4&&b>-1e-4?0:b}).match(zT)||[],t=[],n=0,s=0,r=2/3,o=e.length,a=0,l="ERROR: malformed path: "+i,c,u,f,h,d,g,_,m,p,x,y,S,R,L,w,B=function(b,N,A,I){x=(A-b)/3,y=(I-N)/3,_.push(b+x,N+y,A-x,I-y,A,I)};if(!i||!isNaN(e[0])||isNaN(e[1]))return console.log(l),t;for(c=0;c<o;c++)if(R=d,isNaN(e[c])?(d=e[c].toUpperCase(),g=d!==e[c]):c--,f=+e[c+1],h=+e[c+2],g&&(f+=n,h+=s),c||(m=f,p=h),d==="M")_&&(_.length<8?t.length-=1:a+=_.length,Ld(_)),n=m=f,s=p=h,_=[f,h],t.push(_),c+=2,d="L";else if(d==="C")_||(_=[0,0]),g||(n=s=0),_.push(f,h,n+e[c+3]*1,s+e[c+4]*1,n+=e[c+5]*1,s+=e[c+6]*1),c+=6;else if(d==="S")x=n,y=s,(R==="C"||R==="S")&&(x+=n-_[_.length-4],y+=s-_[_.length-3]),g||(n=s=0),_.push(x,y,f,h,n+=e[c+3]*1,s+=e[c+4]*1),c+=4;else if(d==="Q")x=n+(f-n)*r,y=s+(h-s)*r,g||(n=s=0),n+=e[c+3]*1,s+=e[c+4]*1,_.push(x,y,n+(f-n)*r,s+(h-s)*r,n,s),c+=4;else if(d==="T")x=n-_[_.length-4],y=s-_[_.length-3],_.push(n+x,s+y,f+(n+x*1.5-f)*r,h+(s+y*1.5-h)*r,n=f,s=h),c+=2;else if(d==="H")B(n,s,n=f,s),c+=1;else if(d==="V")B(n,s,n,s=f+(g?s-n:0)),c+=1;else if(d==="L"||d==="Z")d==="Z"&&(f=m,h=p,_.closed=!0),(d==="L"||po(n-f)>.5||po(s-h)>.5)&&(B(n,s,f,h),d==="L"&&(c+=2)),n=f,s=h;else if(d==="A"){if(L=e[c+4],w=e[c+5],x=e[c+6],y=e[c+7],u=7,L.length>1&&(L.length<3?(y=x,x=w,u--):(y=w,x=L.substr(2),u-=2),w=L.charAt(1),L=L.charAt(0)),S=GT(n,s,+e[c+1],+e[c+2],+e[c+3],+L,+w,(g?n:0)+x*1,(g?s:0)+y*1),c+=u,S)for(u=0;u<S.length;u++)_.push(S[u]);n=_[_.length-2],s=_[_.length-1]}else console.log(l);return c=_.length,c<6?(t.pop(),c=0):Ld(_),t.totalPoints=a+c,t}function XT(i){VT(i[0])&&(i=[i]);var e="",t=i.length,n,s,r,o;for(s=0;s<t;s++){for(o=i[s],e+="M"+Hi(o[0])+","+Hi(o[1])+" C",n=o.length,r=2;r<n;r++)e+=Hi(o[r++])+","+Hi(o[r++])+" "+Hi(o[r++])+","+Hi(o[r++])+" "+Hi(o[r++])+","+Hi(o[r])+" ";o.closed&&(e+="z")}return e}/*!
 * CustomEase 3.15.0
 * https://gsap.com
 *
 * @license Copyright 2008-2026, GreenSock. All rights reserved.
 * Subject to the terms at https://gsap.com/standard-license
 * @author: Jack Doyle, jack@greensock.com
*/var ln,p_,m_=function(){return ln||typeof window<"u"&&(ln=window.gsap)&&ln.registerPlugin&&ln},Dd=function(){ln=m_(),ln?(ln.registerEase("_CE",Br.create),p_=1):console.warn("Please gsap.registerPlugin(CustomEase)")},qT=1e20,Sa=function(e){return~~(e*1e3+(e<0?-.5:.5))/1e3},YT=/[-+=.]*\d+[.e\-+]*\d*[e\-+]*\d*/gi,$T=/[cLlsSaAhHvVtTqQ]/g,jT=function(e){var t=e.length,n=qT,s;for(s=1;s<t;s+=6)+e[s]<n&&(n=+e[s]);return n},KT=function(e,t,n){!n&&n!==0&&(n=Math.max(+e[e.length-1],+e[1]));var s=+e[0]*-1,r=-n,o=e.length,a=1/(+e[o-2]+s),l=-t||(Math.abs(+e[o-1]-+e[1])<.01*(+e[o-2]-+e[0])?jT(e)+r:+e[o-1]+r),c;for(l?l=1/l:l=-a,c=0;c<o;c+=2)e[c]=(+e[c]+s)*a,e[c+1]=(+e[c+1]+r)*l},ZT=function i(e,t,n,s,r,o,a,l,c,u,f){var h=(e+n)/2,d=(t+s)/2,g=(n+r)/2,_=(s+o)/2,m=(r+a)/2,p=(o+l)/2,x=(h+g)/2,y=(d+_)/2,S=(g+m)/2,R=(_+p)/2,L=(x+S)/2,w=(y+R)/2,B=a-e,v=l-t,b=Math.abs((n-a)*v-(s-l)*B),N=Math.abs((r-a)*v-(o-l)*B),A;return u||(u=[{x:e,y:t},{x:a,y:l}],f=1),u.splice(f||u.length-1,0,{x:L,y:w}),(b+N)*(b+N)>c*(B*B+v*v)&&(A=u.length,i(e,t,h,d,x,y,L,w,c,u,f),i(L,w,S,R,m,p,a,l,c,u,f+1+(u.length-A))),u},Br=function(){function i(t,n,s){p_||Dd(),this.id=t,this.setData(n,s)}var e=i.prototype;return e.setData=function(n,s){s=s||{},n=n||"0,0,1,1";var r=n.match(YT),o=1,a=[],l=[],c=s.precision||1,u=c<=1,f,h,d,g,_,m,p,x,y;if(this.data=n,($T.test(n)||~n.indexOf("M")&&n.indexOf("C")<0)&&(r=WT(n)[0]),f=r.length,f===4)r.unshift(0,0),r.push(1,1),f=8;else if((f-2)%6)throw"Invalid CustomEase";for((+r[0]!=0||+r[f-2]!=1)&&KT(r,s.height,s.originY),this.segment=r,g=2;g<f;g+=6)h={x:+r[g-2],y:+r[g-1]},d={x:+r[g+4],y:+r[g+5]},a.push(h,d),ZT(h.x,h.y,+r[g],+r[g+1],+r[g+2],+r[g+3],d.x,d.y,1/(c*2e5),a,a.length-1);for(f=a.length,g=0;g<f;g++)p=a[g],x=a[g-1]||p,(p.x>x.x||x.y!==p.y&&x.x===p.x||p===x)&&p.x<=1?(x.cx=p.x-x.x,x.cy=p.y-x.y,x.n=p,x.nx=p.x,u&&g>1&&Math.abs(x.cy/x.cx-a[g-2].cy/a[g-2].cx)>2&&(u=0),x.cx<o&&(x.cx?o=x.cx:(x.cx=.001,g===f-1&&(x.x-=.001,o=Math.min(o,.001),u=0)))):(a.splice(g--,1),f--);if(f=1/o+1|0,_=1/f,m=0,p=a[0],u){for(g=0;g<f;g++)y=g*_,p.nx<y&&(p=a[++m]),h=p.y+(y-p.x)/p.cx*p.cy,l[g]={x:y,cx:_,y:h,cy:0,nx:9},g&&(l[g-1].cy=h-l[g-1].y);m=a[a.length-1],l[f-1].cy=m.y-h,l[f-1].cx=m.x-l[l.length-1].x}else{for(g=0;g<f;g++)p.nx<g*_&&(p=a[++m]),l[g]=p;m<a.length-1&&(l[g-1]=a[a.length-2])}return this.ease=function(S){var R=l[S*f|0]||l[f-1];return R.nx<S&&(R=R.n),R.y+(S-R.x)/R.cx*R.cy},this.ease.custom=this,this.id&&ln&&ln.registerEase(this.id,this.ease),this},e.getSVGData=function(n){return i.getSVGData(this,n)},i.create=function(n,s,r){return new i(n,s,r).ease},i.register=function(n){ln=n,Dd()},i.get=function(n){return ln.parseEase(n)},i.getSVGData=function(n,s){s=s||{};var r=s.width||100,o=s.height||100,a=s.x||0,l=(s.y||0)+o,c=ln.utils.toArray(s.path)[0],u,f,h,d,g,_,m,p,x,y;if(s.invert&&(o=-o,l=0),typeof n=="string"&&(n=ln.parseEase(n)),n.custom&&(n=n.custom),n instanceof i)u=XT(HT([n.segment.slice(0)],r,0,0,-o,a,l));else{for(u=[a,l],m=Math.max(5,(s.precision||1)*200),d=1/m,m+=2,p=5/m,x=Sa(a+d*r),y=Sa(l+n(d)*-o),f=(y-l)/(x-a),h=2;h<m;h++)g=Sa(a+h*d*r),_=Sa(l+n(h*d)*-o),(Math.abs((_-y)/(g-x)-f)>p||h===m-1)&&(u.push(x,y),f=(_-y)/(g-x)),x=g,y=_;u="M"+u.join(",")}return c&&c.setAttribute("d",u),u},i}();Br.version="3.15.0";Br.headless=!0;m_()&&ln.registerPlugin(Br);Ku.registerPlugin(Br);class Ma{constructor(e){this.engine=e,this.timelines=[],this.currentTimeline=null,this.isPlaying=!1,this.customEases=new Map,this.currentEaseParams={x1:.25,y1:.1,x2:.25,y2:1},this.currentEaseName="custom_bezier"}registerCustomEase(e,t){const{x1:n,y1:s,x2:r,y2:o}=t,a=`M0,0 C${n},${s} ${r},${o} 1,1`;try{return Br.create(e,a),this.customEases.set(e,{params:t,easeString:a}),!0}catch(l){return console.error("Failed to register custom ease:",l),!1}}getBezierEase(e){const{x1:t,y1:n,x2:s,y2:r}=e,o=`bezier_${t}_${n}_${s}_${r}`.replace(/\./g,"p");return this.customEases.has(o)||this.registerCustomEase(o,e),o}createTimeline(e={}){const t=Ku.timeline({paused:!0,repeat:e.repeat||0,yoyo:e.yoyo||!1,onComplete:()=>{this.isPlaying=!1}});return this.timelines.push(t),this.currentTimeline=t,t}addKeyframe(e,t){const{time:n,properties:s,duration:r=.5,ease:o="power2.inOut",bezier:a=null}=t,l=JSON.parse(JSON.stringify(this.engine.config));let c=o;a&&(c=this.getBezierEase(a));const u={};this.buildTargetProps(l,s,u),e.to(this.engine.config,{...u,duration:r,ease:c,delay:n,onUpdate:()=>{this.engine.updateConfig({})}})}buildTargetProps(e,t,n,s=""){for(const r in t){const o=s?`${s}.${r}`:r;typeof t[r]=="object"&&!Array.isArray(t[r])?this.buildTargetProps(e[r],t[r],n,o):n[o]=t[r]}}createAnimationFromKeyframes(e,t={}){const n=this.createTimeline(t);e.sort((s,r)=>s.time-r.time);for(let s=0;s<e.length;s++){const r=e[s],o=e[s+1],a=o?o.time-r.time:.5;this.addKeyframe(n,{time:s===0?0:e[s-1].time,properties:r.properties,duration:a,ease:r.ease||"power2.inOut",bezier:r.bezier||null})}return n}createPresetAnimation(e,t=null){const n={pulse:[{time:0,properties:{emissionRate:100,size:{min:.1,max:.3}},ease:"power2.inOut"},{time:1,properties:{emissionRate:500,size:{min:.3,max:.8}},ease:"power2.inOut"},{time:2,properties:{emissionRate:100,size:{min:.1,max:.3}},ease:"power2.inOut"}],colorShift:[{time:0,properties:{color:{start:"#ff0000",end:"#ff6600"}},ease:"power1.inOut"},{time:2,properties:{color:{start:"#00ff00",end:"#00ff66"}},ease:"power1.inOut"},{time:4,properties:{color:{start:"#0000ff",end:"#6600ff"}},ease:"power1.inOut"},{time:6,properties:{color:{start:"#ff0000",end:"#ff6600"}},ease:"power1.inOut"}],explosion:[{time:0,properties:{emissionRate:10,speed:{min:1,max:3}},ease:"power4.out"},{time:.5,properties:{emissionRate:1e3,speed:{min:5,max:15}},ease:"power4.out"},{time:1,properties:{emissionRate:50,speed:{min:1,max:3}},ease:"power2.out"}],spiral:[{time:0,properties:{direction:{x:1,y:0,z:0},emitterPosition:{x:0,y:0,z:0}},ease:"none"},{time:2,properties:{direction:{x:0,y:1,z:0},emitterPosition:{x:2,y:0,z:0}},ease:"none"},{time:4,properties:{direction:{x:-1,y:0,z:0},emitterPosition:{x:0,y:2,z:0}},ease:"none"},{time:6,properties:{direction:{x:0,y:-1,z:0},emitterPosition:{x:-2,y:0,z:0}},ease:"none"},{time:8,properties:{direction:{x:1,y:0,z:0},emitterPosition:{x:0,y:-2,z:0}},ease:"none"}]};let s=n[e]||n.pulse;return t&&(s=s.map(r=>({...r,ease:null,bezier:t}))),this.createAnimationFromKeyframes(s,{repeat:-1,yoyo:!1})}setCustomBezierEase(e){this.currentEaseParams={...e},this.registerCustomEase(this.currentEaseName,e)}playAnimationWithCustomEase(e,t){this.stopAll(),this.createPresetAnimation(e,t),this.play()}play(e=this.currentTimeline){e&&(e.play(),this.isPlaying=!0)}pause(e=this.currentTimeline){e&&(e.pause(),this.isPlaying=!1)}restart(e=this.currentTimeline){e&&(e.restart(),this.isPlaying=!0)}seek(e,t=this.currentTimeline){t&&t.seek(e)}stop(e=this.currentTimeline){e&&(e.pause(0),this.isPlaying=!1)}stopAll(){this.timelines.forEach(e=>e.pause(0)),this.isPlaying=!1}dispose(){this.stopAll(),this.timelines.forEach(e=>e.kill()),this.timelines=[],this.currentTimeline=null,this.customEases.clear()}}class JT{constructor(e,t,n){this.canvas=e,this.particleEngine=t,this.camera=n,this.enabled=!0,this.mode="repel",this.strength=50,this.radius=5,this.falloff=2,this.isMouseDown=!1,this.isDragging=!1,this.mousePosition=new $,this.lastMousePosition=new $,this.mouseVelocity=new $,this.raycaster=new hb,this.ndc=new He,this.plane=new Si(new $(0,0,1),0),this.interactionPoints=[],this.maxInteractionPoints=10,this.bindEvents()}bindEvents(){this.canvas.addEventListener("mousedown",this.onMouseDown.bind(this)),this.canvas.addEventListener("mousemove",this.onMouseMove.bind(this)),this.canvas.addEventListener("mouseup",this.onMouseUp.bind(this)),this.canvas.addEventListener("mouseleave",this.onMouseUp.bind(this)),this.canvas.addEventListener("wheel",this.onWheel.bind(this)),this.canvas.addEventListener("touchstart",this.onTouchStart.bind(this),{passive:!1}),this.canvas.addEventListener("touchmove",this.onTouchMove.bind(this),{passive:!1}),this.canvas.addEventListener("touchend",this.onTouchEnd.bind(this))}getMouseWorldPosition(e,t){const n=this.canvas.getBoundingClientRect();this.ndc.x=(e-n.left)/n.width*2-1,this.ndc.y=-((t-n.top)/n.height)*2+1,this.raycaster.setFromCamera(this.ndc,this.camera);const s=new $;return this.raycaster.ray.intersectPlane(this.plane,s),s||new $}onMouseDown(e){this.enabled&&(this.isMouseDown=!0,this.isDragging=!0,this.mousePosition.copy(this.getMouseWorldPosition(e.clientX,e.clientY)),this.lastMousePosition.copy(this.mousePosition),this.addInteractionPoint(this.mousePosition.clone(),!0))}onMouseMove(e){if(!this.enabled)return;const t=this.getMouseWorldPosition(e.clientX,e.clientY);this.isDragging?(this.mouseVelocity.copy(t).sub(this.lastMousePosition),this.mousePosition.copy(t),this.lastMousePosition.copy(t),this.addInteractionPoint(this.mousePosition.clone(),!1)):this.mousePosition.copy(t)}onMouseUp(){this.isMouseDown=!1,this.isDragging=!1,this.mouseVelocity.set(0,0,0)}onWheel(e){}onTouchStart(e){if(e.preventDefault(),!this.enabled||e.touches.length===0)return;const t=e.touches[0];this.onMouseDown({clientX:t.clientX,clientY:t.clientY})}onTouchMove(e){if(e.preventDefault(),!this.enabled||e.touches.length===0)return;const t=e.touches[0];this.onMouseMove({clientX:t.clientX,clientY:t.clientY})}onTouchEnd(){this.onMouseUp()}addInteractionPoint(e,t){const n={position:e.clone(),strength:t?this.strength*2:this.strength,radius:this.radius,falloff:this.falloff,lifetime:t?.5:.1,age:0,mode:this.mode,isClick:t};this.interactionPoints.push(n),this.interactionPoints.length>this.maxInteractionPoints&&this.interactionPoints.shift()}update(e){if(!(!this.enabled||this.interactionPoints.length===0||!this.particleEngine))for(let t=this.interactionPoints.length-1;t>=0;t--){const n=this.interactionPoints[t];if(n.age+=e,n.age>=n.lifetime){this.interactionPoints.splice(t,1);continue}const s=1-n.age/n.lifetime,r=n.strength*s;this.applyForceToParticles(n.position,r,n.radius,n.falloff,n.mode)}}applyForceToParticles(e,t,n,s,r){if(!this.particleEngine.activeIndices)return;const o=this.particleEngine.instancePosition,a=this.particleEngine.instanceVelocity,l=n*n;for(const c of this.particleEngine.activeIndices){const u=c*3,f=o[u]-e.x,h=o[u+1]-e.y,d=o[u+2]-e.z,g=f*f+h*h+d*d;if(g>l)continue;const _=Math.sqrt(g)||.001,m=t*Math.pow(1-_/n,s);let p,x,y;switch(r){case"attract":p=-f/_*m,x=-h/_*m,y=-d/_*m;break;case"repel":p=f/_*m,x=h/_*m,y=d/_*m;break;case"vortex":p=-h/_*m,x=f/_*m,y=0;break;case"upward":p=0,x=m,y=0;break;case"downward":p=0,x=-m,y=0;break;default:p=f/_*m,x=h/_*m,y=d/_*m}a[u]+=p,a[u+1]+=x,a[u+2]+=y}this.particleEngine.geometry.attributes.instanceVelocity.needsUpdate=!0}setMode(e){this.mode=e}setStrength(e){this.strength=e}setRadius(e){this.radius=e}setEnabled(e){this.enabled=e}dispose(){this.canvas.removeEventListener("mousedown",this.onMouseDown),this.canvas.removeEventListener("mousemove",this.onMouseMove),this.canvas.removeEventListener("mouseup",this.onMouseUp),this.canvas.removeEventListener("mouseleave",this.onMouseUp),this.canvas.removeEventListener("wheel",this.onWheel),this.canvas.removeEventListener("touchstart",this.onTouchStart),this.canvas.removeEventListener("touchmove",this.onTouchMove),this.canvas.removeEventListener("touchend",this.onTouchEnd),this.interactionPoints=[]}}const Bo={maxParticles:1e6,particleCount:5e4,emissionRate:5e3,speed:{min:1,max:3},life:{min:1,max:3},size:{min:.1,max:.5},color:{start:"#ff6600",end:"#ff0000"},direction:{x:0,y:1,z:0},spread:.5,gravity:{x:0,y:-.5,z:0},emitterPosition:{x:0,y:0,z:0},emitterShape:"point",emitterRadius:1,rotationSpeed:{min:0,max:2},blending:"additive"},Fr={fire:{maxParticles:1e6,particleCount:15e4,emissionRate:3e4,speed:{min:2,max:5},life:{min:.5,max:1.5},size:{min:.2,max:.8},color:{start:"#ffff00",end:"#ff0000"},direction:{x:0,y:1,z:0},spread:.6,gravity:{x:0,y:-1,z:0},emitterPosition:{x:0,y:-2,z:0},emitterShape:"circle",emitterRadius:.5,rotationSpeed:{min:0,max:3},blending:"additive"},smoke:{maxParticles:5e5,particleCount:8e4,emissionRate:8e3,speed:{min:.5,max:1.5},life:{min:2,max:5},size:{min:.5,max:1.5},color:{start:"#888888",end:"#333333"},direction:{x:0,y:1,z:0},spread:.8,gravity:{x:0,y:.2,z:0},emitterPosition:{x:0,y:-2,z:0},emitterShape:"circle",emitterRadius:.3,rotationSpeed:{min:.5,max:2},blending:"normal"},stars:{maxParticles:2e6,particleCount:5e5,emissionRate:5e4,speed:{min:.05,max:.2},life:{min:3,max:8},size:{min:.05,max:.2},color:{start:"#ffffff",end:"#88ccff"},direction:{x:0,y:0,z:0},spread:0,gravity:{x:0,y:0,z:0},emitterPosition:{x:0,y:0,z:0},emitterShape:"sphere",emitterRadius:20,rotationSpeed:{min:0,max:1},blending:"additive"},snow:{maxParticles:1e6,particleCount:2e5,emissionRate:15e3,speed:{min:.3,max:1},life:{min:5,max:10},size:{min:.1,max:.4},color:{start:"#ffffff",end:"#aaddff"},direction:{x:0,y:-1,z:0},spread:.3,gravity:{x:0,y:-.1,z:0},emitterPosition:{x:0,y:8,z:0},emitterShape:"box",emitterRadius:15,rotationSpeed:{min:1,max:4},blending:"additive"}};function Zu(i,e=Bo){const t={};for(const n in i){if(!(n in e)){t[n]=JSON.parse(JSON.stringify(i[n]));continue}const s=i[n],r=e[n];if(typeof s=="object"&&!Array.isArray(s)&&s!==null)if(typeof r=="object"&&!Array.isArray(r)&&r!==null){const o=Zu(s,r);Object.keys(o).length>0&&(t[n]=o)}else t[n]=JSON.parse(JSON.stringify(s));else s!==r&&(t[n]=s)}return t}function __(i,e=Bo){const t=JSON.parse(JSON.stringify(e));for(const n in i){const s=i[n];typeof s=="object"&&!Array.isArray(s)&&s!==null?typeof t[n]=="object"&&!Array.isArray(t[n])&&t[n]!==null?t[n]=__(s,t[n]):t[n]=JSON.parse(JSON.stringify(s)):t[n]=s}return t}function g_(i,e={},t={}){const{useDiff:n=!0,basePreset:s=null,prettyPrint:r=!0}=t,o={version:"2.0.0",exportedAt:new Date().toISOString(),format:n?"diff":"full",metadata:{name:e.name||"粒子特效",description:e.description||"",author:e.author||"",basePreset:s,...e}};if(n){const a=s&&Fr[s]?Fr[s]:Bo;o.diff=Zu(i,a),o.basePreset=s}else o.config=JSON.parse(JSON.stringify(i));return JSON.stringify(o,null,r?2:0)}function QT(i){var e,t;try{const n=JSON.parse(i);let s;const r=n.format==="diff"&&n.diff;if(r){const a=n.basePreset||((e=n.metadata)==null?void 0:e.basePreset),l=a&&Fr[a]?Fr[a]:Bo;s=__(n.diff,l)}else{if(!n.config)throw new Error("配置文件格式错误：缺少 config 字段");s=n.config}const o=e1(s);if(!o.valid)throw new Error(`配置验证失败：缺少字段 ${o.missingFields.join(", ")}`);return{success:!0,data:s,metadata:n.metadata||{},version:n.version,format:r?"diff":"full",basePreset:n.basePreset||((t=n.metadata)==null?void 0:t.basePreset)}}catch(n){return{success:!1,error:n.message}}}function v_(i,e="particle-effect.json",t={},n={}){const s=g_(i,t,n),r=new Blob([s],{type:"application/json"}),o=URL.createObjectURL(r),a=document.createElement("a");a.href=o,a.download=e,document.body.appendChild(a),a.click(),document.body.removeChild(a),URL.revokeObjectURL(o)}function x_(i){return new Promise((e,t)=>{const n=new FileReader;n.onload=s=>{const r=QT(s.target.result);r.success?e(r):t(new Error(r.error))},n.onerror=()=>{t(new Error("文件读取失败"))},n.readAsText(i)})}function e1(i){const t=["maxParticles","particleCount","emissionRate","speed","life","size","color","direction","spread","gravity","emitterPosition","emitterShape","emitterRadius","rotationSpeed","blending"].filter(n=>!(n in i));return t.length>0?{valid:!1,missingFields:t}:{valid:!0}}function t1(i,e=null){const t=e&&Fr[e]?Fr[e]:Bo,n=JSON.stringify(i),s=Zu(i,t),r=JSON.stringify(s);return{fullSize:n.length,diffSize:r.length,saved:n.length-r.length,savedPercent:Math.round((1-r.length/n.length)*100)}}const Ud="particle_user_templates",n1=[{id:"community-001",name:"炫酷火焰爆炸",author:"Community",category:"fire",icon:"🔥",description:"高强度火焰爆炸效果，适合游戏特效",downloads:1245,likes:892,config:{particleCount:2e5,emissionRate:5e4,speed:{min:3,max:8},life:{min:.3,max:1},size:{min:.3,max:1.2},color:{start:"#ffff00",end:"#ff0000"},direction:{x:0,y:1,z:0},spread:1.2,gravity:{x:0,y:-2,z:0},emitterShape:"sphere",emitterRadius:.3,blending:"additive"}},{id:"community-002",name:"梦幻紫色烟雾",author:"Community",category:"smoke",icon:"💜",description:"优雅的紫色烟雾，适合魔法效果",downloads:876,likes:654,config:{particleCount:1e5,emissionRate:5e3,speed:{min:.3,max:1},life:{min:3,max:6},size:{min:.8,max:2},color:{start:"#cc88ff",end:"#440088"},direction:{x:0,y:1,z:0},spread:.4,gravity:{x:0,y:.1,z:0},emitterShape:"circle",emitterRadius:.5,blending:"normal"}},{id:"community-003",name:"极光星空",author:"Community",category:"stars",icon:"🌌",description:"美丽的极光粒子效果",downloads:1567,likes:1123,config:{particleCount:3e5,emissionRate:3e4,speed:{min:.02,max:.1},life:{min:5,max:12},size:{min:.05,max:.15},color:{start:"#00ff88",end:"#0088ff"},direction:{x:0,y:0,z:0},spread:.1,gravity:{x:0,y:0,z:0},emitterShape:"sphere",emitterRadius:25,blending:"additive"}},{id:"community-004",name:"金色雪花",author:"Community",category:"snow",icon:"🌟",description:"闪闪发光的金色雪花",downloads:789,likes:567,config:{particleCount:15e4,emissionRate:1e4,speed:{min:.2,max:.8},life:{min:4,max:8},size:{min:.15,max:.35},color:{start:"#ffdd00",end:"#ffaa00"},direction:{x:0,y:-1,z:0},spread:.2,gravity:{x:0,y:-.05,z:0},emitterShape:"box",emitterRadius:18,blending:"additive"}},{id:"community-005",name:"绿色火焰",author:"Community",category:"fire",icon:"💚",description:"神秘的绿色火焰",downloads:654,likes:432,config:{particleCount:12e4,emissionRate:25e3,speed:{min:2,max:6},life:{min:.4,max:1.2},size:{min:.2,max:.9},color:{start:"#00ff00",end:"#004400"},direction:{x:0,y:1,z:0},spread:.7,gravity:{x:0,y:-1.5,z:0},emitterShape:"circle",emitterRadius:.4,blending:"additive"}},{id:"community-006",name:"彩虹粒子",author:"Community",category:"special",icon:"🌈",description:"七彩流动粒子效果",downloads:2134,likes:1876,config:{particleCount:25e4,emissionRate:4e4,speed:{min:1,max:3},life:{min:1,max:4},size:{min:.15,max:.5},color:{start:"#ffffff",end:"#ffffff"},direction:{x:0,y:1,z:0},spread:.8,gravity:{x:0,y:-.5,z:0},emitterShape:"sphere",emitterRadius:.5,blending:"additive"}}];let y_=class{constructor(){this.templates=[...n1],this.userTemplates=this.loadUserTemplates(),this.categories=[{id:"all",name:"全部",icon:"🌐"},{id:"fire",name:"火焰",icon:"🔥"},{id:"smoke",name:"烟雾",icon:"💨"},{id:"stars",name:"星空",icon:"✨"},{id:"snow",name:"雪花",icon:"❄️"},{id:"special",name:"特殊",icon:"💫"},{id:"user",name:"我的",icon:"👤"}],this.currentCategory="all",this.searchQuery="",this.sortBy="popular"}loadUserTemplates(){try{const e=localStorage.getItem(Ud);return e?JSON.parse(e):[]}catch(e){return console.error("Failed to load user templates:",e),[]}}saveUserTemplates(){try{localStorage.setItem(Ud,JSON.stringify(this.userTemplates))}catch(e){console.error("Failed to save user templates:",e)}}getTemplates(){let e=[...this.templates];if(this.currentCategory==="user"?e=[...this.userTemplates]:this.currentCategory!=="all"&&(e=e.filter(t=>t.category===this.currentCategory)),this.searchQuery){const t=this.searchQuery.toLowerCase();e=e.filter(n=>n.name.toLowerCase().includes(t)||n.description.toLowerCase().includes(t))}switch(this.sortBy){case"popular":e.sort((t,n)=>(n.downloads||0)-(t.downloads||0));break;case"latest":e.sort((t,n)=>new Date(n.createdAt||0)-new Date(t.createdAt||0));break;case"likes":e.sort((t,n)=>(n.likes||0)-(t.likes||0));break}return e}getTemplateById(e){return this.templates.find(t=>t.id===e)||this.userTemplates.find(t=>t.id===e)}getCategories(){return this.categories}setCategory(e){this.currentCategory=e}setSearchQuery(e){this.searchQuery=e}setSortBy(e){this.sortBy=e}saveUserTemplate(e,t,n=""){const s={id:`user-${Date.now()}`,name:e,author:"Me",category:"user",icon:"🎨",description:n,downloads:0,likes:0,createdAt:new Date().toISOString(),config:JSON.parse(JSON.stringify(t))};return this.userTemplates.unshift(s),this.saveUserTemplates(),s}deleteUserTemplate(e){const t=this.userTemplates.findIndex(n=>n.id===e);return t!==-1?(this.userTemplates.splice(t,1),this.saveUserTemplates(),!0):!1}downloadTemplate(e){const t=`template-${e.name.toLowerCase().replace(/\s+/g,"-")}-${Date.now()}.json`;v_(e.config,t,{name:e.name,author:e.author,description:e.description}),e.id.startsWith("user-")||(e.downloads=(e.downloads||0)+1)}likeTemplate(e){e.id.startsWith("user-")||(e.likes=(e.likes||0)+1)}async importTemplateFromFile(e){try{const t=await x_(e);return{id:`user-${Date.now()}`,name:e.name.replace(".json",""),author:"Imported",category:"user",icon:"📁",description:"从文件导入",createdAt:new Date().toISOString(),config:t.data}}catch(t){throw new Error("导入失败: "+t.message)}}exportTemplate(e){return g_(e.config,{name:e.name,author:e.author,description:e.description,templateId:e.id})}shareTemplate(e){const t={title:e.name,text:e.description,url:`https://particle-editor.app/template/${e.id}`};return navigator.share?navigator.share(t):Promise.resolve({...t,shared:!0})}};const ko=(i,e)=>{const t=i.__vccOpts||i;for(const[n,s]of e)t[n]=s;return t},i1={class:"bezier-editor"},s1={class:"editor-header"},r1={class:"preset-curves"},o1=["onClick","title"],a1={key:0,class:"control-point-info"},l1={class:"editor-footer"},c1={class:"curve-params"},u1={class:"param-item"},f1={class:"param-value"},Zt=280,dt=20,h1={__name:"BezierEditor",props:{modelValue:{type:Object,default:()=>({x1:.25,y1:.1,x2:.25,y2:1})},presetName:{type:String,default:""}},emits:["update:modelValue","apply"],setup(i,{emit:e}){const t=i,n=e,s=tt(null),r=tt(null),o=tt([{x:0,y:1},{x:.25,y:.1},{x:.25,y:1},{x:1,y:0}]),a=tt(null),l=tt(""),c=[{name:"linear",icon:"─",params:{x1:0,y1:0,x2:1,y2:1}},{name:"ease",icon:"⌒",params:{x1:.25,y1:.1,x2:.25,y2:1}},{name:"ease-in",icon:"╭",params:{x1:.42,y1:0,x2:1,y2:1}},{name:"ease-out",icon:"╮",params:{x1:0,y1:0,x2:.58,y2:1}},{name:"ease-in-out",icon:"〜",params:{x1:.42,y1:0,x2:.58,y2:1}},{name:"power2.in",icon:"²↑",params:{x1:.55,y1:.085,x2:.68,y2:.53}},{name:"power2.out",icon:"²↓",params:{x1:.25,y1:.46,x2:.45,y2:.94}},{name:"power4.in",icon:"⁴↑",params:{x1:.895,y1:.03,x2:.685,y2:.22}},{name:"power4.out",icon:"⁴↓",params:{x1:.165,y1:.84,x2:.44,y2:1}},{name:"elastic",icon:"∿",params:{x1:.68,y1:-.55,x2:.265,y2:1.55}},{name:"back-in",icon:"↶",params:{x1:.6,y1:-.28,x2:.735,y2:.045}},{name:"back-out",icon:"↷",params:{x1:.175,y1:.885,x2:.32,y2:1.275}}];xr(()=>t.modelValue,v=>{v&&(o.value[1]={x:v.x1,y:v.y1},o.value[2]={x:v.x2,y:v.y2},S())},{deep:!0}),xr(o,()=>{const v={x1:o.value[1].x,y1:o.value[1].y,x2:o.value[2].x,y2:o.value[2].y};n("update:modelValue",v),l.value="",S()},{deep:!0});function u(v){return l.value===v.name}function f(v){o.value[1]={x:v.params.x1,y:v.params.y1},o.value[2]={x:v.params.x2,y:v.params.y2},l.value=v.name,S()}function h(){const v=o.value[1],b=o.value[2];return`${v.x.toFixed(2)}, ${v.y.toFixed(2)}, ${b.x.toFixed(2)}, ${b.y.toFixed(2)}`}function d(){o.value[1]={x:.25,y:.1},o.value[2]={x:.25,y:1},l.value="",S()}function g(){n("apply",{x1:o.value[1].x,y1:o.value[1].y,x2:o.value[2].x,y2:o.value[2].y,preset:l.value})}function _(v){return dt+v*(Zt-dt*2)}function m(v){return Zt-dt-v*(Zt-dt*2)}function p(v){return(v-dt)/(Zt-dt*2)}function x(v){return(Zt-dt-v)/(Zt-dt*2)}function y(v){const b=o.value[0],N=o.value[1],A=o.value[2],I=o.value[3],O=1-v,k=O*O,H=k*O,q=v*v,Z=q*v;return{x:H*b.x+3*k*v*N.x+3*O*q*A.x+Z*I.x,y:H*b.y+3*k*v*N.y+3*O*q*A.y+Z*I.y}}function S(){if(!s.value)return;const v=s.value.getContext("2d"),b=Zt;v.clearRect(0,0,b,b),v.fillStyle="#0f0f1a",v.fillRect(0,0,b,b),v.strokeStyle="rgba(255, 255, 255, 0.05)",v.lineWidth=1;for(let A=0;A<=10;A++){const I=dt+A/10*(b-dt*2);v.beginPath(),v.moveTo(I,dt),v.lineTo(I,b-dt),v.stroke(),v.beginPath(),v.moveTo(dt,I),v.lineTo(b-dt,I),v.stroke()}v.strokeStyle="rgba(255, 255, 255, 0.2)",v.lineWidth=2,v.setLineDash([5,5]),v.beginPath(),v.moveTo(_(0),m(0)),v.lineTo(_(o.value[1].x),m(o.value[1].y)),v.stroke(),v.beginPath(),v.moveTo(_(1),m(0)),v.lineTo(_(o.value[2].x),m(o.value[2].y)),v.stroke(),v.setLineDash([]),v.strokeStyle="#667eea",v.lineWidth=3,v.beginPath();for(let A=0;A<=1;A+=.01){const I=y(A),O=_(I.x),k=m(I.y);A===0?v.moveTo(O,k):v.lineTo(O,k)}v.stroke();const N=v.createLinearGradient(0,b,b,0);N.addColorStop(0,"rgba(102, 126, 234, 0.1)"),N.addColorStop(1,"rgba(118, 75, 162, 0.1)"),v.fillStyle=N,v.beginPath(),v.moveTo(_(0),m(0));for(let A=0;A<=1;A+=.01){const I=y(A);v.lineTo(_(I.x),m(I.y))}v.lineTo(_(1),m(0)),v.closePath(),v.fill();for(let A=0;A<o.value.length;A++){const I=o.value[A],O=_(I.x),k=m(I.y);A===0||A===3?(v.fillStyle="rgba(255, 255, 255, 0.3)",v.beginPath(),v.arc(O,k,6,0,Math.PI*2),v.fill()):(v.fillStyle="rgba(255, 255, 255, 0.9)",v.strokeStyle="#667eea",v.lineWidth=2,v.beginPath(),v.arc(O,k,10,0,Math.PI*2),v.fill(),v.stroke(),v.fillStyle="#667eea",v.font="bold 10px monospace",v.textAlign="center",v.textBaseline="middle",v.fillText(`P${A}`,O,k))}v.fillStyle="rgba(255, 255, 255, 0.5)",v.font="10px monospace",v.textAlign="left",v.fillText("0",dt-15,b-dt+4),v.textAlign="right",v.fillText("1",b-dt+15,b-dt+4),v.textAlign="right",v.textBaseline="middle",v.fillText("1",dt-8,dt),v.fillText("0",dt-8,b-dt)}function R(v,b){for(let N=1;N<=2;N++){const A=o.value[N],I=_(A.x),O=m(A.y);if(Math.sqrt((v-I)**2+(b-O)**2)<15)return N}return null}function L(v){const b=s.value.getBoundingClientRect(),N=Zt/b.width,A=Zt/b.height,I=(v.clientX-b.left)*N,O=(v.clientY-b.top)*A,k=R(I,O);k!==null&&(a.value=k)}function w(v){if(a.value===null)return;const b=s.value.getBoundingClientRect(),N=Zt/b.width,A=Zt/b.height;let I=(v.clientX-b.left)*N,O=(v.clientY-b.top)*A;I=Math.max(dt-50,Math.min(Zt-dt+50,I)),O=Math.max(dt-50,Math.min(Zt-dt+50,O)),o.value[a.value]={x:Math.max(-.5,Math.min(1.5,p(I))),y:Math.max(-.5,Math.min(1.5,x(O)))}}function B(){a.value=null}return yu(()=>{t.modelValue&&(o.value[1]={x:t.modelValue.x1,y:t.modelValue.y1},o.value[2]={x:t.modelValue.x2,y:t.modelValue.y2}),S()}),(v,b)=>(rt(),lt("div",i1,[C("div",s1,[b[0]||(b[0]=C("h4",null,"贝塞尔曲线编辑器",-1)),C("div",r1,[(rt(),lt(Nt,null,Ti(c,N=>C("button",{key:N.name,class:en(["preset-btn",{active:u(N)}]),onClick:A=>f(N),title:N.name},Fe(N.icon),11,o1)),64))])]),C("div",{class:"canvas-container",ref_key:"canvasContainer",ref:r},[C("canvas",{ref_key:"canvas",ref:s,width:Zt,height:Zt,onMousedown:L,onMousemove:w,onMouseup:B,onMouseleave:B},null,544),a.value!==null?(rt(),lt("div",a1,[C("span",null,"P"+Fe(a.value)+": ("+Fe(o.value[a.value].x.toFixed(2))+", "+Fe(o.value[a.value].y.toFixed(2))+")",1)])):wi("",!0)],512),C("div",l1,[C("div",c1,[C("div",u1,[b[1]||(b[1]=C("span",null,"cubic-bezier(",-1)),C("span",f1,Fe(h()),1),b[2]||(b[2]=C("span",null,")",-1))])]),C("div",{class:"editor-actions"},[C("button",{onClick:d,class:"reset-btn"},"重置"),C("button",{onClick:g,class:"apply-btn"},"应用")])])]))}},d1=ko(h1,[["__scopeId","data-v-df9b1540"]]);class p1{constructor(){this.audioContext=null,this.analyser=null,this.dataArray=null,this.source=null,this.audioElement=null,this.enabled=!1,this.initialized=!1,this.fftSize=2048,this.smoothingTimeConstant=.8,this.bass=0,this.mid=0,this.treble=0,this.volume=0,this.sensitivity=1.5,this.bassMultiplier=2,this.midMultiplier=1,this.trebleMultiplier=.8,this.reactiveParams={emissionRate:{enabled:!0,intensity:1,freqBand:"bass"},speed:{enabled:!0,intensity:.5,freqBand:"mid"},size:{enabled:!0,intensity:.3,freqBand:"treble"},color:{enabled:!1,intensity:1,freqBand:"mid"}},this.onUpdate=null}async init(){try{return this.audioContext=new(window.AudioContext||window.webkitAudioContext),this.analyser=this.audioContext.createAnalyser(),this.analyser.fftSize=this.fftSize,this.analyser.smoothingTimeConstant=this.smoothingTimeConstant,this.dataArray=new Uint8Array(this.analyser.frequencyBinCount),this.initialized=!0,!0}catch(e){return console.error("Failed to initialize audio context:",e),!1}}async connectToMicrophone(){if(!this.initialized&&!await this.init())return!1;try{const e=await navigator.mediaDevices.getUserMedia({audio:!0});return this.source=this.audioContext.createMediaStreamSource(e),this.source.connect(this.analyser),this.enabled=!0,!0}catch(e){return console.error("Failed to connect to microphone:",e),!1}}async connectToAudioElement(e){if(!this.initialized&&!await this.init())return!1;try{return this.audioElement=e,this.source=this.audioContext.createMediaElementSource(e),this.source.connect(this.analyser),this.analyser.connect(this.audioContext.destination),this.enabled=!0,!0}catch(t){return console.error("Failed to connect to audio element:",t),!1}}loadAudioFile(e){return new Promise((t,n)=>{const s=new Audio;s.src=URL.createObjectURL(e),s.crossOrigin="anonymous",s.loop=!0,s.addEventListener("loadedmetadata",async()=>{await this.connectToAudioElement(s),t(s)}),s.addEventListener("error",r=>{n(r)})})}update(){if(!this.enabled||!this.analyser)return;this.analyser.getByteFrequencyData(this.dataArray);const e=this.dataArray.length,t=Math.floor(e*.1),n=Math.floor(e*.5);let s=0,r=0,o=0;for(let a=0;a<t;a++)s+=this.dataArray[a];for(let a=t;a<n;a++)r+=this.dataArray[a];for(let a=n;a<e;a++)o+=this.dataArray[a];this.bass=s/t/255*this.sensitivity*this.bassMultiplier,this.mid=r/(n-t)/255*this.sensitivity*this.midMultiplier,this.treble=o/(e-n)/255*this.sensitivity*this.trebleMultiplier,this.volume=(this.bass+this.mid+this.treble)/3,this.onUpdate&&this.onUpdate({bass:this.bass,mid:this.mid,treble:this.treble,volume:this.volume})}getFreqBand(e){switch(e){case"bass":return this.bass;case"mid":return this.mid;case"treble":return this.treble;case"volume":return this.volume;default:return this.volume}}applyToParticleConfig(e){if(!this.enabled)return e;const t={...e};for(const[n,s]of Object.entries(this.reactiveParams)){if(!s.enabled)continue;const r=this.getFreqBand(s.freqBand),o=s.intensity;switch(n){case"emissionRate":typeof t.emissionRate=="number"&&(t.emissionRate=Math.floor(t.emissionRate*(1+r*o)));break;case"speed":t.speed&&typeof t.speed.min=="number"&&(t.speed={min:t.speed.min*(1+r*o*.5),max:t.speed.max*(1+r*o)});break;case"size":t.size&&typeof t.size.min=="number"&&(t.size={min:t.size.min*(1+r*o*.5),max:t.size.max*(1+r*o)});break;case"color":if(t.color&&t.color.start){const a=this.hexToRgb(t.color.start),l=r*o,c={r:Math.min(255,Math.floor(a.r*(1+l))),g:Math.min(255,Math.floor(a.g*(1+l*.5))),b:Math.min(255,Math.floor(a.b*(1+l*.3)))};t.color={start:this.rgbToHex(c.r,c.g,c.b),end:t.color.end}}break}}return t}hexToRgb(e){const t=/^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(e);return t?{r:parseInt(t[1],16),g:parseInt(t[2],16),b:parseInt(t[3],16)}:{r:255,g:255,b:255}}rgbToHex(e,t,n){return"#"+[e,t,n].map(s=>{const r=Math.max(0,Math.min(255,s)).toString(16);return r.length===1?"0"+r:r}).join("")}setSensitivity(e){this.sensitivity=e}setReactiveParam(e,t){this.reactiveParams[e]&&Object.assign(this.reactiveParams[e],t)}play(){this.audioElement&&this.audioElement.play()}pause(){this.audioElement&&this.audioElement.pause()}stop(){this.enabled=!1,this.audioElement&&(this.audioElement.pause(),this.audioElement.currentTime=0),this.source&&(this.source.disconnect(),this.source=null),this.audioContext&&(this.audioContext.close(),this.audioContext=null,this.initialized=!1),this.bass=0,this.mid=0,this.treble=0,this.volume=0}dispose(){this.stop(),this.onUpdate=null}}const m1={class:"interaction-panel"},_1={class:"panel-section"},g1={class:"section-header"},v1={class:"toggle-switch"},x1=["checked"],y1={key:0,class:"section-content"},S1={class:"control-item"},M1={class:"mode-buttons"},E1=["onClick"],b1={class:"control-item"},T1={class:"control-item"},A1={class:"panel-section"},w1={class:"section-header"},R1={class:"toggle-switch"},C1=["checked"],P1={key:0,class:"section-content"},L1={class:"control-item"},D1={class:"audio-sources"},U1={class:"source-btn file-input-label"},I1={key:0,class:"audio-controls"},O1={class:"control-item"},N1={class:"audio-visualizer"},F1={class:"freq-bars"},z1={class:"reactive-params"},B1={class:"param-item"},k1={class:"mini-toggle"},V1=["checked"],H1={class:"param-item"},G1={class:"mini-toggle"},W1=["checked"],X1={class:"param-item"},q1={class:"mini-toggle"},Y1=["checked"],$1={key:0,class:"audio-player"},j1={key:1,class:"audio-hint"},K1={__name:"InteractionPanel",props:{mouseInteractor:{type:Object,default:null}},emits:["mouse-enabled-change","audio-enabled-change","audio-reactor-created"],setup(i,{emit:e}){const t=i,n=e,s=tt(!1),r=tt("repel"),o=tt(50),a=tt(5),l=tt(!1),c=tt(null),u=tt(!1),f=tt(1.5),h=new p1,d=tt(null),g=tt(!1),_=tt(0),m=tt(0),p=tt(0),x=tt({emissionRate:{enabled:!0,intensity:1,freqBand:"bass"},speed:{enabled:!0,intensity:.5,freqBand:"mid"},size:{enabled:!0,intensity:.3,freqBand:"treble"},color:{enabled:!1,intensity:1,freqBand:"mid"}}),y=[{id:"repel",name:"排斥",icon:"↗️"},{id:"attract",name:"吸引",icon:"↘️"},{id:"vortex",name:"漩涡",icon:"🌀"},{id:"upward",name:"上升",icon:"⬆️"},{id:"downward",name:"下降",icon:"⬇️"}],S=lo(()=>`${Math.min(100,_.value*80)}%`),R=lo(()=>`${Math.min(100,m.value*80)}%`),L=lo(()=>`${Math.min(100,p.value*80)}%`);function w(j){s.value=j.target.checked,t.mouseInteractor&&t.mouseInteractor.setEnabled(s.value),n("mouse-enabled-change",s.value)}function B(j){r.value=j,t.mouseInteractor&&t.mouseInteractor.setMode(j)}function v(){t.mouseInteractor&&t.mouseInteractor.setStrength(o.value)}function b(){t.mouseInteractor&&t.mouseInteractor.setRadius(a.value)}function N(j){l.value=j.target.checked,l.value||(h.stop(),u.value=!1),n("audio-enabled-change",l.value)}async function A(){c.value="mic",await h.connectToMicrophone()&&(u.value=!0,h.onUpdate=O,n("audio-reactor-created",h),k())}async function I(j){const G=j.target.files[0];if(G)try{c.value="file";const re=await h.loadAudioFile(G);d.value=re,u.value=!0,h.onUpdate=O,n("audio-reactor-created",h),k()}catch(re){alert("加载音频文件失败: "+re.message)}j.target.value=""}function O(j){_.value=j.bass,m.value=j.mid,p.value=j.treble}function k(){function j(){u.value&&l.value&&(h.update(),requestAnimationFrame(j))}requestAnimationFrame(j)}function H(){h.setSensitivity(f.value)}function q(j){const G=x.value[j];G&&(G.enabled=!G.enabled,h.setReactiveParam(j,G))}function Z(){g.value?(h.pause(),g.value=!1):(h.play(),g.value=!0)}function W(){d.value&&(d.value.pause(),d.value.currentTime=0,g.value=!1)}return ul(()=>{h.dispose()}),(j,G)=>(rt(),lt("div",m1,[C("div",_1,[C("div",g1,[G[7]||(G[7]=C("h5",null,"🖱️ 鼠标交互",-1)),C("label",v1,[C("input",{type:"checkbox",checked:s.value,onChange:w},null,40,x1),G[6]||(G[6]=C("span",{class:"toggle-slider"},null,-1))])]),s.value?(rt(),lt("div",y1,[C("div",S1,[G[8]||(G[8]=C("label",null,"交互模式",-1)),C("div",M1,[(rt(),lt(Nt,null,Ti(y,re=>C("button",{key:re.id,class:en(["mode-btn",{active:r.value===re.id}]),onClick:Q=>B(re.id)},Fe(re.icon)+" "+Fe(re.name),11,E1)),64))])]),C("div",b1,[C("label",null,"力度: "+Fe(o.value.toFixed(0)),1),$e(C("input",{type:"range",min:"10",max:"200",step:"5","onUpdate:modelValue":G[0]||(G[0]=re=>o.value=re),onInput:v},null,544),[[ot,o.value,void 0,{number:!0}]])]),C("div",T1,[C("label",null,"半径: "+Fe(a.value.toFixed(1)),1),$e(C("input",{type:"range",min:"1",max:"20",step:"0.5","onUpdate:modelValue":G[1]||(G[1]=re=>a.value=re),onInput:b},null,544),[[ot,a.value,void 0,{number:!0}]])]),G[9]||(G[9]=C("div",{class:"hint"}," 💡 点击或拖拽鼠标与粒子互动 ",-1))])):wi("",!0)]),C("div",A1,[C("div",w1,[G[11]||(G[11]=C("h5",null,"🎵 音频驱动",-1)),C("label",R1,[C("input",{type:"checkbox",checked:l.value,onChange:N},null,40,C1),G[10]||(G[10]=C("span",{class:"toggle-slider"},null,-1))])]),l.value?(rt(),lt("div",P1,[C("div",L1,[G[13]||(G[13]=C("label",null,"音频源",-1)),C("div",D1,[C("button",{class:en(["source-btn",{active:c.value==="mic"}]),onClick:A}," 🎤 麦克风 ",2),C("label",U1,[G[12]||(G[12]=ws(" 📁 音频文件 ",-1)),C("input",{type:"file",accept:"audio/*",onChange:I,style:{display:"none"}},null,32)])])]),u.value?(rt(),lt("div",I1,[C("div",O1,[C("label",null,"灵敏度: "+Fe(f.value.toFixed(1)),1),$e(C("input",{type:"range",min:"0.5",max:"3",step:"0.1","onUpdate:modelValue":G[2]||(G[2]=re=>f.value=re),onInput:H},null,544),[[ot,f.value,void 0,{number:!0}]])]),C("div",N1,[C("div",F1,[C("div",{class:"freq-bar bass",style:gr({height:S.value})},null,4),C("div",{class:"freq-bar mid",style:gr({height:R.value})},null,4),C("div",{class:"freq-bar treble",style:gr({height:L.value})},null,4)]),G[14]||(G[14]=C("div",{class:"freq-labels"},[C("span",null,"低频"),C("span",null,"中频"),C("span",null,"高频")],-1))]),C("div",z1,[C("div",B1,[G[16]||(G[16]=C("label",null,"发射速率",-1)),C("label",k1,[C("input",{type:"checkbox",checked:x.value.emissionRate.enabled,onChange:G[3]||(G[3]=re=>q("emissionRate"))},null,40,V1),G[15]||(G[15]=ws(" 启用 ",-1))])]),C("div",H1,[G[18]||(G[18]=C("label",null,"粒子速度",-1)),C("label",G1,[C("input",{type:"checkbox",checked:x.value.speed.enabled,onChange:G[4]||(G[4]=re=>q("speed"))},null,40,W1),G[17]||(G[17]=ws(" 启用 ",-1))])]),C("div",X1,[G[20]||(G[20]=C("label",null,"粒子大小",-1)),C("label",q1,[C("input",{type:"checkbox",checked:x.value.size.enabled,onChange:G[5]||(G[5]=re=>q("size"))},null,40,Y1),G[19]||(G[19]=ws(" 启用 ",-1))])])]),d.value?(rt(),lt("div",$1,[C("button",{onClick:Z,class:"play-btn"},Fe(g.value?"⏸":"▶"),1),C("button",{onClick:W,class:"stop-btn"},"⏹")])):wi("",!0)])):(rt(),lt("div",j1," 💡 连接音频源以控制粒子动态 "))])):wi("",!0)])]))}},Z1=ko(K1,[["__scopeId","data-v-012e56af"]]),J1={class:"template-market"},Q1={class:"market-header"},eA={class:"market-actions"},tA={class:"file-input-label"},nA={class:"market-toolbar"},iA={class:"categories"},sA=["onClick"],rA={class:"search-sort"},oA={class:"templates-grid"},aA={class:"card-header"},lA={class:"template-icon"},cA={class:"template-name"},uA={class:"card-body"},fA={class:"template-description"},hA={class:"template-meta"},dA={key:0},pA={key:1},mA={class:"card-footer"},_A=["onClick"],gA={class:"card-actions"},vA=["onClick"],xA=["onClick"],yA=["onClick"],SA={key:0,class:"empty-state"},MA={__name:"TemplateMarket",emits:["apply-template","save-current","import-template"],setup(i,{emit:e}){const t=new y_,n=tt(t.getCategories()),s=tt("all"),r=tt(""),o=tt("popular"),a=lo(()=>(t.setCategory(s.value),t.setSearchQuery(r.value),t.setSortBy(o.value),t.getTemplates()));function l(m){s.value=m}function c(){t.setSearchQuery(r.value)}function u(m){o.value=m.target.value,t.setSortBy(o.value)}function f(m){t.downloadTemplate(m)}function h(m){t.likeTemplate(m)}function d(m){confirm(`确定要删除 "${m.name}" 吗？`)&&t.deleteUserTemplate(m.id)}async function g(m){const p=m.target.files[0];if(p)try{const x=await t.importTemplateFromFile(p);t.userTemplates.unshift(x),t.saveUserTemplates()}catch(x){alert(x.message)}m.target.value=""}function _(m){return m>=1e3?(m/1e3).toFixed(1)+"k":m.toString()}return(m,p)=>(rt(),lt("div",J1,[C("div",Q1,[p[4]||(p[4]=C("h4",null,"粒子模板市场",-1)),C("div",eA,[C("button",{onClick:p[0]||(p[0]=x=>m.$emit("save-current")),class:"action-btn"},"💾 保存当前"),C("label",tA,[p[3]||(p[3]=ws(" 📂 导入 ",-1)),C("input",{type:"file",accept:".json",onChange:g,style:{display:"none"}},null,32)])])]),C("div",nA,[C("div",iA,[(rt(!0),lt(Nt,null,Ti(n.value,x=>(rt(),lt("button",{key:x.id,class:en(["category-btn",{active:s.value===x.id}]),onClick:y=>l(x.id)},Fe(x.icon)+" "+Fe(x.name),11,sA))),128))]),C("div",rA,[$e(C("input",{type:"text","onUpdate:modelValue":p[1]||(p[1]=x=>r.value=x),placeholder:"🔍 搜索模板...",class:"search-input",onInput:c},null,544),[[ot,r.value]]),$e(C("select",{"onUpdate:modelValue":p[2]||(p[2]=x=>o.value=x),onChange:u,class:"sort-select"},[...p[5]||(p[5]=[C("option",{value:"popular"},"🔥 最热",-1),C("option",{value:"latest"},"🆕 最新",-1),C("option",{value:"likes"},"👍 最多赞",-1)])],544),[[Ic,o.value]])])]),C("div",oA,[(rt(!0),lt(Nt,null,Ti(a.value,x=>(rt(),lt("div",{key:x.id,class:"template-card"},[C("div",aA,[C("span",lA,Fe(x.icon),1),C("span",cA,Fe(x.name),1)]),C("div",uA,[C("p",fA,Fe(x.description),1),C("div",hA,[C("span",null,"👤 "+Fe(x.author),1),x.downloads?(rt(),lt("span",dA,"📥 "+Fe(_(x.downloads)),1)):wi("",!0),x.likes?(rt(),lt("span",pA,"👍 "+Fe(_(x.likes)),1)):wi("",!0)])]),C("div",mA,[C("button",{onClick:y=>m.$emit("apply-template",x),class:"apply-btn"}," ✨ 使用 ",8,_A),C("div",gA,[C("button",{onClick:y=>f(x),class:"icon-btn",title:"下载"}," 📥 ",8,vA),C("button",{onClick:y=>h(x),class:"icon-btn",title:"点赞"}," 👍 ",8,xA),x.author==="Me"||x.category==="user"?(rt(),lt("button",{key:0,onClick:y=>d(x),class:"icon-btn",title:"删除"}," 🗑️ ",8,yA)):wi("",!0)])])]))),128)),a.value.length===0?(rt(),lt("div",SA,[...p[6]||(p[6]=[C("span",{class:"empty-icon"},"📭",-1),C("p",null,"暂无模板",-1)])])):wi("",!0)])]))}},EA=ko(MA,[["__scopeId","data-v-c43f289c"]]),bA={class:"control-panel"},TA={class:"panel-header"},AA={class:"preset-buttons"},wA=["onClick"],RA={class:"panel-tabs"},CA=["onClick"],PA={class:"panel-content"},LA={class:"control-group"},DA={class:"control-item"},UA={class:"range-control"},IA={class:"value"},OA={class:"control-item"},NA={class:"range-control"},FA={class:"value"},zA={class:"control-item"},BA={class:"range-control"},kA={class:"value"},VA={class:"control-group"},HA={class:"control-item"},GA={class:"dual-range"},WA={class:"range-item"},XA={class:"value"},qA={class:"range-item"},YA={class:"value"},$A={class:"control-item"},jA={class:"dual-range"},KA={class:"range-item"},ZA={class:"value"},JA={class:"range-item"},QA={class:"value"},ew={class:"control-item"},tw={class:"vector-control"},nw={class:"vector-item"},iw={class:"vector-item"},sw={class:"vector-item"},rw={class:"control-item"},ow={class:"vector-control"},aw={class:"vector-item"},lw={class:"vector-item"},cw={class:"vector-item"},uw={class:"control-item"},fw={class:"range-control"},hw={class:"value"},dw={class:"control-group"},pw={class:"control-item"},mw={class:"dual-range"},_w={class:"range-item"},gw={class:"value"},vw={class:"range-item"},xw={class:"value"},yw={class:"control-item"},Sw={class:"color-control"},Mw={class:"color-item"},Ew={class:"color-value"},bw={class:"color-item"},Tw={class:"color-value"},Aw={class:"control-item"},ww={class:"dual-range"},Rw={class:"range-item"},Cw={class:"value"},Pw={class:"range-item"},Lw={class:"value"},Dw={class:"control-item"},Uw={class:"control-group"},Iw={class:"control-item"},Ow={class:"control-item"},Nw={class:"range-control"},Fw={class:"value"},zw={class:"control-item"},Bw={class:"vector-control"},kw={class:"vector-item"},Vw={class:"vector-item"},Hw={class:"vector-item"},Gw={class:"control-group"},Ww={class:"control-item"},Xw={class:"animation-buttons"},qw=["onClick"],Yw={class:"control-item"},$w={class:"ease-options"},jw=["onClick"],Kw={key:0,class:"control-item"},Zw={class:"control-item"},Jw={class:"animation-controls"},Qw={class:"control-item"},eR={class:"animation-controls"},tR=["onClick"],nR={class:"control-group"},iR={class:"control-group"},sR={class:"panel-footer"},rR={class:"playback-controls"},oR={class:"io-controls"},aR={class:"file-input-label"},lR={__name:"ControlPanel",props:{config:{type:Object,required:!0},currentPreset:{type:String,default:"fire"},isPlaying:{type:Boolean,default:!0},mouseInteractor:{type:Object,default:null}},emits:["load-preset","update-config","play","pause","reset","export","import","play-animation","animation-play","animation-pause","animation-restart","animation-stop","play-animation-with-bezier","apply-bezier-ease","apply-template","save-template"],setup(i,{emit:e}){const t=i,n=e,s=tt("basic"),r=Wi,o=tt("pulse"),a=tt("power2.inOut"),l=tt(!1),c=tt({x1:.25,y1:.1,x2:.25,y2:1}),u=[{key:"basic",label:"基础",icon:"⚙️"},{key:"physics",label:"物理",icon:"🎯"},{key:"appearance",label:"外观",icon:"🎨"},{key:"emitter",label:"发射器",icon:"💫"},{key:"animation",label:"动画",icon:"🎬"},{key:"interaction",label:"交互",icon:"🖱️"},{key:"market",label:"市场",icon:"🛒"}],f=[{key:"pulse",label:"脉冲",icon:"💓"},{key:"colorShift",label:"变色",icon:"🌈"},{key:"explosion",label:"爆炸",icon:"💥"},{key:"spiral",label:"螺旋",icon:"🌀"}],h=[{key:"power1.inOut",label:"Power1"},{key:"power2.inOut",label:"Power2"},{key:"power3.inOut",label:"Power3"},{key:"power4.inOut",label:"Power4"},{key:"elastic.out",label:"Elastic"},{key:"back.inOut",label:"Back"}],d=tt(JSON.parse(JSON.stringify(t.config)));function g(N){o.value=N}function _(N){a.value=N,l.value=!1}function m(){l.value=!l.value}function p(){n("play-animation",o.value)}function x(N){n("apply-bezier-ease",N)}function y(N){n("play-animation-with-bezier",{animation:N,bezier:c.value})}xr(()=>t.config,N=>{d.value=JSON.parse(JSON.stringify(N))},{deep:!0});function S(){n("update-config",JSON.parse(JSON.stringify(d.value)))}async function R(N){const A=N.target.files[0];if(A)try{const I=await x_(A);n("import",I.data)}catch(I){alert("导入失败: "+I.message)}N.target.value=""}function L(N){console.log("Mouse interaction:",N)}function w(N){console.log("Audio reactor:",N)}function B(N){n("audio-reactor-created",N)}function v(N){n("apply-template",N)}function b(){const N=prompt("输入模板名称:","我的特效");N&&n("save-template",{name:N,config:JSON.parse(JSON.stringify(d.value))})}return(N,A)=>(rt(),lt("div",bA,[C("div",TA,[A[34]||(A[34]=C("h2",null,"粒子特效编辑器",-1)),C("div",AA,[(rt(!0),lt(Nt,null,Ti(gu(r),(I,O)=>(rt(),lt("button",{key:O,class:en(["preset-btn",{active:i.currentPreset===O}]),onClick:k=>N.$emit("load-preset",O)},Fe(I.icon)+" "+Fe(I.name),11,wA))),128))])]),C("div",RA,[(rt(),lt(Nt,null,Ti(u,I=>C("button",{key:I.key,class:en(["tab-btn",{active:s.value===I.key}]),onClick:O=>s.value=I.key},Fe(I.icon)+" "+Fe(I.label),11,CA)),64))]),C("div",PA,[$e(C("div",LA,[A[38]||(A[38]=C("h3",null,"基础参数",-1)),C("div",DA,[A[35]||(A[35]=C("label",null,"粒子数量",-1)),C("div",UA,[$e(C("input",{type:"range",min:100,max:1e4,step:100,"onUpdate:modelValue":A[0]||(A[0]=I=>d.value.particleCount=I),onInput:S},null,544),[[ot,d.value.particleCount,void 0,{number:!0}]]),C("span",IA,Fe(d.value.particleCount),1)])]),C("div",OA,[A[36]||(A[36]=C("label",null,"发射速率",-1)),C("div",NA,[$e(C("input",{type:"range",min:1,max:1e3,step:1,"onUpdate:modelValue":A[1]||(A[1]=I=>d.value.emissionRate=I),onInput:S},null,544),[[ot,d.value.emissionRate,void 0,{number:!0}]]),C("span",FA,Fe(d.value.emissionRate)+"/s",1)])]),C("div",zA,[A[37]||(A[37]=C("label",null,"最大粒子数",-1)),C("div",BA,[$e(C("input",{type:"range",min:1e3,max:2e4,step:500,"onUpdate:modelValue":A[2]||(A[2]=I=>d.value.maxParticles=I),onInput:S},null,544),[[ot,d.value.maxParticles,void 0,{number:!0}]]),C("span",kA,Fe(d.value.maxParticles),1)])])],512),[[ps,s.value==="basic"]]),$e(C("div",VA,[A[54]||(A[54]=C("h3",null,"物理参数",-1)),C("div",HA,[A[41]||(A[41]=C("label",null,"速度范围",-1)),C("div",GA,[C("div",WA,[A[39]||(A[39]=C("span",null,"最小",-1)),$e(C("input",{type:"range",min:.1,max:20,step:.1,"onUpdate:modelValue":A[3]||(A[3]=I=>d.value.speed.min=I),onInput:S},null,544),[[ot,d.value.speed.min,void 0,{number:!0}]]),C("span",XA,Fe(d.value.speed.min.toFixed(1)),1)]),C("div",qA,[A[40]||(A[40]=C("span",null,"最大",-1)),$e(C("input",{type:"range",min:.1,max:20,step:.1,"onUpdate:modelValue":A[4]||(A[4]=I=>d.value.speed.max=I),onInput:S},null,544),[[ot,d.value.speed.max,void 0,{number:!0}]]),C("span",YA,Fe(d.value.speed.max.toFixed(1)),1)])])]),C("div",$A,[A[44]||(A[44]=C("label",null,"生命周期",-1)),C("div",jA,[C("div",KA,[A[42]||(A[42]=C("span",null,"最小",-1)),$e(C("input",{type:"range",min:.1,max:10,step:.1,"onUpdate:modelValue":A[5]||(A[5]=I=>d.value.life.min=I),onInput:S},null,544),[[ot,d.value.life.min,void 0,{number:!0}]]),C("span",ZA,Fe(d.value.life.min.toFixed(1))+"s",1)]),C("div",JA,[A[43]||(A[43]=C("span",null,"最大",-1)),$e(C("input",{type:"range",min:.1,max:10,step:.1,"onUpdate:modelValue":A[6]||(A[6]=I=>d.value.life.max=I),onInput:S},null,544),[[ot,d.value.life.max,void 0,{number:!0}]]),C("span",QA,Fe(d.value.life.max.toFixed(1))+"s",1)])])]),C("div",ew,[A[48]||(A[48]=C("label",null,"重力",-1)),C("div",tw,[C("div",nw,[A[45]||(A[45]=C("span",null,"X",-1)),$e(C("input",{type:"number",step:.1,"onUpdate:modelValue":A[7]||(A[7]=I=>d.value.gravity.x=I),onInput:S},null,544),[[ot,d.value.gravity.x,void 0,{number:!0}]])]),C("div",iw,[A[46]||(A[46]=C("span",null,"Y",-1)),$e(C("input",{type:"number",step:.1,"onUpdate:modelValue":A[8]||(A[8]=I=>d.value.gravity.y=I),onInput:S},null,544),[[ot,d.value.gravity.y,void 0,{number:!0}]])]),C("div",sw,[A[47]||(A[47]=C("span",null,"Z",-1)),$e(C("input",{type:"number",step:.1,"onUpdate:modelValue":A[9]||(A[9]=I=>d.value.gravity.z=I),onInput:S},null,544),[[ot,d.value.gravity.z,void 0,{number:!0}]])])])]),C("div",rw,[A[52]||(A[52]=C("label",null,"发射方向",-1)),C("div",ow,[C("div",aw,[A[49]||(A[49]=C("span",null,"X",-1)),$e(C("input",{type:"number",step:.1,"onUpdate:modelValue":A[10]||(A[10]=I=>d.value.direction.x=I),onInput:S},null,544),[[ot,d.value.direction.x,void 0,{number:!0}]])]),C("div",lw,[A[50]||(A[50]=C("span",null,"Y",-1)),$e(C("input",{type:"number",step:.1,"onUpdate:modelValue":A[11]||(A[11]=I=>d.value.direction.y=I),onInput:S},null,544),[[ot,d.value.direction.y,void 0,{number:!0}]])]),C("div",cw,[A[51]||(A[51]=C("span",null,"Z",-1)),$e(C("input",{type:"number",step:.1,"onUpdate:modelValue":A[12]||(A[12]=I=>d.value.direction.z=I),onInput:S},null,544),[[ot,d.value.direction.z,void 0,{number:!0}]])])])]),C("div",uw,[A[53]||(A[53]=C("label",null,"扩散角度",-1)),C("div",fw,[$e(C("input",{type:"range",min:0,max:2,step:.01,"onUpdate:modelValue":A[13]||(A[13]=I=>d.value.spread=I),onInput:S},null,544),[[ot,d.value.spread,void 0,{number:!0}]]),C("span",hw,Fe(d.value.spread.toFixed(2)),1)])])],512),[[ps,s.value==="physics"]]),$e(C("div",dw,[A[66]||(A[66]=C("h3",null,"外观参数",-1)),C("div",pw,[A[57]||(A[57]=C("label",null,"大小范围",-1)),C("div",mw,[C("div",_w,[A[55]||(A[55]=C("span",null,"最小",-1)),$e(C("input",{type:"range",min:.01,max:3,step:.01,"onUpdate:modelValue":A[14]||(A[14]=I=>d.value.size.min=I),onInput:S},null,544),[[ot,d.value.size.min,void 0,{number:!0}]]),C("span",gw,Fe(d.value.size.min.toFixed(2)),1)]),C("div",vw,[A[56]||(A[56]=C("span",null,"最大",-1)),$e(C("input",{type:"range",min:.01,max:3,step:.01,"onUpdate:modelValue":A[15]||(A[15]=I=>d.value.size.max=I),onInput:S},null,544),[[ot,d.value.size.max,void 0,{number:!0}]]),C("span",xw,Fe(d.value.size.max.toFixed(2)),1)])])]),C("div",yw,[A[60]||(A[60]=C("label",null,"颜色",-1)),C("div",Sw,[C("div",Mw,[A[58]||(A[58]=C("span",null,"起始",-1)),$e(C("input",{type:"color","onUpdate:modelValue":A[16]||(A[16]=I=>d.value.color.start=I),onInput:S},null,544),[[ot,d.value.color.start]]),C("span",Ew,Fe(d.value.color.start),1)]),C("div",bw,[A[59]||(A[59]=C("span",null,"结束",-1)),$e(C("input",{type:"color","onUpdate:modelValue":A[17]||(A[17]=I=>d.value.color.end=I),onInput:S},null,544),[[ot,d.value.color.end]]),C("span",Tw,Fe(d.value.color.end),1)])])]),C("div",Aw,[A[63]||(A[63]=C("label",null,"旋转速度",-1)),C("div",ww,[C("div",Rw,[A[61]||(A[61]=C("span",null,"最小",-1)),$e(C("input",{type:"range",min:0,max:10,step:.1,"onUpdate:modelValue":A[18]||(A[18]=I=>d.value.rotationSpeed.min=I),onInput:S},null,544),[[ot,d.value.rotationSpeed.min,void 0,{number:!0}]]),C("span",Cw,Fe(d.value.rotationSpeed.min.toFixed(1)),1)]),C("div",Pw,[A[62]||(A[62]=C("span",null,"最大",-1)),$e(C("input",{type:"range",min:0,max:10,step:.1,"onUpdate:modelValue":A[19]||(A[19]=I=>d.value.rotationSpeed.max=I),onInput:S},null,544),[[ot,d.value.rotationSpeed.max,void 0,{number:!0}]]),C("span",Lw,Fe(d.value.rotationSpeed.max.toFixed(1)),1)])])]),C("div",Dw,[A[65]||(A[65]=C("label",null,"混合模式",-1)),$e(C("select",{"onUpdate:modelValue":A[20]||(A[20]=I=>d.value.blending=I),onChange:S},[...A[64]||(A[64]=[C("option",{value:"additive"},"加法混合",-1),C("option",{value:"normal"},"正常混合",-1)])],544),[[Ic,d.value.blending]])])],512),[[ps,s.value==="appearance"]]),$e(C("div",Uw,[A[74]||(A[74]=C("h3",null,"发射器参数",-1)),C("div",Iw,[A[68]||(A[68]=C("label",null,"发射器形状",-1)),$e(C("select",{"onUpdate:modelValue":A[21]||(A[21]=I=>d.value.emitterShape=I),onChange:S},[...A[67]||(A[67]=[C("option",{value:"point"},"点",-1),C("option",{value:"circle"},"圆形",-1),C("option",{value:"sphere"},"球体",-1),C("option",{value:"box"},"立方体",-1)])],544),[[Ic,d.value.emitterShape]])]),C("div",Ow,[A[69]||(A[69]=C("label",null,"发射器半径",-1)),C("div",Nw,[$e(C("input",{type:"range",min:.1,max:30,step:.1,"onUpdate:modelValue":A[22]||(A[22]=I=>d.value.emitterRadius=I),onInput:S},null,544),[[ot,d.value.emitterRadius,void 0,{number:!0}]]),C("span",Fw,Fe(d.value.emitterRadius.toFixed(1)),1)])]),C("div",zw,[A[73]||(A[73]=C("label",null,"发射器位置",-1)),C("div",Bw,[C("div",kw,[A[70]||(A[70]=C("span",null,"X",-1)),$e(C("input",{type:"number",step:.1,"onUpdate:modelValue":A[23]||(A[23]=I=>d.value.emitterPosition.x=I),onInput:S},null,544),[[ot,d.value.emitterPosition.x,void 0,{number:!0}]])]),C("div",Vw,[A[71]||(A[71]=C("span",null,"Y",-1)),$e(C("input",{type:"number",step:.1,"onUpdate:modelValue":A[24]||(A[24]=I=>d.value.emitterPosition.y=I),onInput:S},null,544),[[ot,d.value.emitterPosition.y,void 0,{number:!0}]])]),C("div",Hw,[A[72]||(A[72]=C("span",null,"Z",-1)),$e(C("input",{type:"number",step:.1,"onUpdate:modelValue":A[25]||(A[25]=I=>d.value.emitterPosition.z=I),onInput:S},null,544),[[ot,d.value.emitterPosition.z,void 0,{number:!0}]])])])])],512),[[ps,s.value==="emitter"]]),$e(C("div",Gw,[A[79]||(A[79]=C("h3",null,"关键帧动画",-1)),C("div",Ww,[A[75]||(A[75]=C("label",null,"预设动画",-1)),C("div",Xw,[(rt(),lt(Nt,null,Ti(f,I=>C("button",{key:I.key,class:en(["anim-btn",{active:o.value===I.key}]),onClick:O=>g(I.key)},Fe(I.icon)+" "+Fe(I.label),11,qw)),64))])]),C("div",Yw,[A[76]||(A[76]=C("label",null,"缓动曲线",-1)),C("div",$w,[(rt(),lt(Nt,null,Ti(h,I=>C("button",{key:I.key,class:en(["ease-btn",{active:a.value===I.key&&!l.value}]),onClick:O=>_(I.key)},Fe(I.label),11,jw)),64)),C("button",{class:en(["ease-btn",{active:l.value}]),onClick:m}," 自定义 ",2)])]),l.value?(rt(),lt("div",Kw,[bn(d1,{modelValue:c.value,"onUpdate:modelValue":A[26]||(A[26]=I=>c.value=I),onApply:x},null,8,["modelValue"])])):wi("",!0),C("div",Zw,[A[77]||(A[77]=C("label",null,"动画控制",-1)),C("div",Jw,[C("button",{onClick:p},"▶ 播放"),C("button",{onClick:A[27]||(A[27]=I=>N.$emit("animation-pause"))},"⏸ 暂停"),C("button",{onClick:A[28]||(A[28]=I=>N.$emit("animation-restart"))},"↻ 重放"),C("button",{onClick:A[29]||(A[29]=I=>N.$emit("animation-stop"))},"⏹ 停止")])]),C("div",Qw,[A[78]||(A[78]=C("label",null,"使用自定义曲线播放",-1)),C("div",eR,[(rt(),lt(Nt,null,Ti(f,I=>C("button",{key:"bezier-"+I.key,class:"anim-btn small",onClick:O=>y(I.key)},Fe(I.icon)+" "+Fe(I.label),9,tR)),64))])])],512),[[ps,s.value==="animation"]]),$e(C("div",nR,[bn(Z1,{"mouse-interactor":i.mouseInteractor,onMouseEnabledChange:L,onAudioEnabledChange:w,onAudioReactorCreated:B},null,8,["mouse-interactor"])],512),[[ps,s.value==="interaction"]]),$e(C("div",iR,[bn(EA,{onApplyTemplate:v,onSaveCurrent:b})],512),[[ps,s.value==="market"]])]),C("div",sR,[C("div",rR,[C("button",{onClick:A[30]||(A[30]=I=>N.$emit("play")),class:en({active:i.isPlaying})},"▶ 播放",2),C("button",{onClick:A[31]||(A[31]=I=>N.$emit("pause")),class:en({active:!i.isPlaying})},"⏸ 暂停",2),C("button",{onClick:A[32]||(A[32]=I=>N.$emit("reset"))},"↻ 重置")]),C("div",oR,[C("label",aR,[A[80]||(A[80]=ws(" 📂 导入 ",-1)),C("input",{type:"file",accept:".json",onChange:R,style:{display:"none"}},null,32)]),C("button",{onClick:A[33]||(A[33]=I=>N.$emit("export"))},"💾 导出")])])]))}},cR=ko(lR,[["__scopeId","data-v-215bb97e"]]),uR={class:"app"},fR={class:"status-bar"},hR={class:"status-item"},dR={class:"status-value"},pR={class:"status-item"},mR={class:"status-value"},_R={class:"status-item"},gR={class:"status-value"},vR={class:"status-item"},xR={__name:"App",setup(i){const e=tt(null),t=tt("fire"),n=tt(!0),s=tt(60),r=tt(0);let o=null,a=null,l=null,c=null,u=null,f=0,h=0,d=null;const g=JSON.parse(JSON.stringify(Wi.fire.config)),_=al(JSON.parse(JSON.stringify(g)));function m(W){var j;return((j=Wi[W])==null?void 0:j.name)||W}function p(){if(!e.value)return;o=new vb(e.value),a=o.addParticleSystem(t.value),l=new Ma(a);const W=e.value.querySelector("canvas");W&&o.camera&&(c=new JT(W,a,o.camera)),u=new y_,x()}function x(){f++;const W=performance.now();W-h>=1e3&&(s.value=f,f=0,h=W),a&&(r.value=a.particles.length),d=requestAnimationFrame(x)}function y(W){if(!o||!Wi[W])return;t.value=W;const j=Wi[W].config;Object.assign(_,JSON.parse(JSON.stringify(j))),o.clearAllParticleSystems(),a=o.addParticleSystem(W),l&&l.dispose(),l=new Ma(a)}function S(W){a&&(Object.assign(_,W),a.updateConfig(W))}function R(){o&&(o.play(),n.value=!0)}function L(){o&&(o.pause(),n.value=!1)}function w(){o&&o.reset()}function B(){if(!a)return;const W=a.getConfig(),j=Wi[t.value]?t.value:null,G=t1(W,j);console.log(`导出配置：完整大小 ${G.fullSize} 字节，差量大小 ${G.diffSize} 字节，节省 ${G.savedPercent}%`);const re=`particle-${t.value}-${Date.now()}.json`;v_(W,re,{name:m(t.value),preset:t.value,sizeInfo:G},{useDiff:!0,basePreset:j,prettyPrint:!0})}function v(W){o&&(Object.assign(_,W),o.clearAllParticleSystems(),a=o.addParticleSystem("fire",W),l&&l.dispose(),l=new Ma(a),t.value="custom")}function b(W){l&&(l.stopAll(),l.createPresetAnimation(W),l.play())}function N(){l&&l.play()}function A(){l&&l.pause()}function I(){l&&l.restart()}function O(){l&&l.stopAll()}function k({animation:W,bezier:j}){l&&(console.log(`使用自定义贝塞尔曲线播放动画 ${W}:`,j),l.stopAll(),l.playAnimationWithCustomEase(W,j))}function H(W){l&&(console.log("应用贝塞尔缓动:",W),l.setCustomBezierEase(W))}function q(W){!o||!W.config||(console.log("应用模板:",W.name),Object.assign(_,JSON.parse(JSON.stringify(W.config))),o.clearAllParticleSystems(),a=o.addParticleSystem("fire",W.config),l&&l.dispose(),l=new Ma(a),c&&(c.particleEngine=a),t.value=W.name)}function Z({name:W,config:j}){if(!u)return;const G=u.saveUserTemplate(W,j,"用户保存的特效");console.log("保存模板:",G.name),alert(`模板 "${W}" 已保存！`)}return yu(()=>{p()}),ul(()=>{d&&cancelAnimationFrame(d),l&&l.dispose(),c&&c.dispose(),o&&o.dispose()}),(W,j)=>(rt(),lt("div",uR,[C("div",{class:"canvas-container",ref_key:"canvasContainer",ref:e},null,512),bn(cR,{config:_,"current-preset":t.value,"is-playing":n.value,"mouse-interactor":gu(c),onLoadPreset:y,onUpdateConfig:S,onPlay:R,onPause:L,onReset:w,onExport:B,onImport:v,onPlayAnimation:b,onAnimationPlay:N,onAnimationPause:A,onAnimationRestart:I,onAnimationStop:O,onPlayAnimationWithBezier:k,onApplyBezierEase:H,onApplyTemplate:q,onSaveTemplate:Z},null,8,["config","current-preset","is-playing","mouse-interactor"]),C("div",fR,[C("div",hR,[j[0]||(j[0]=C("span",{class:"status-label"},"FPS",-1)),C("span",dR,Fe(s.value),1)]),C("div",pR,[j[1]||(j[1]=C("span",{class:"status-label"},"粒子数",-1)),C("span",mR,Fe(r.value),1)]),C("div",_R,[j[2]||(j[2]=C("span",{class:"status-label"},"当前预设",-1)),C("span",gR,Fe(m(t.value)),1)]),C("div",vR,[j[3]||(j[3]=C("span",{class:"status-label"},"状态",-1)),C("span",{class:en(["status-value",{playing:n.value}])},Fe(n.value?"播放中":"已暂停"),3)])])]))}},yR=ko(xR,[["__scopeId","data-v-743517fd"]]);q0(yR).mount("#app");
