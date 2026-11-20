const test=require('node:test'), assert=require('node:assert/strict');
const {atlasClearance:c}=require('../static/field-tools.js');
test('flat short path has antenna clearance',()=>assert.equal(c({d:10,z:[50,50]},6,8).gap,6));
test('ridge obstructs path, and raising A improves midpoint clearance',()=>{const p={d:1000,z:[10,30,10]};assert.equal(c(p,6,6).at,500);assert(c(p,6,6).gap<-14);assert(c(p,40,6).gap>0);});
test('curvature obstructs a long flat path',()=>assert(c({d:100000,z:[0,0,0]},2,2).gap<-140));
test('co-located endpoints',()=>assert.equal(c({d:0,z:[20,20]},0,10).gap,0));
test('invalid input is not clear',()=>assert.throws(()=>c({d:20,z:[1,NaN]},6,6)));
