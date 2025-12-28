//DragContext unit tests - verifies drag state management
import{describe,it,expect,vi,beforeEach}from'vitest'
import{render,act}from'@testing-library/react'
import{DragProvider,useDrag}from'./DragContext'
//Test component that exposes DragContext internals
function TestConsumer({onMount}:{onMount:(api:ReturnType<typeof useDrag>)=>void}){
const api=useDrag()
onMount(api)
return <div data-testid="consumer">ready</div>
}
describe('DragContext',()=>{
let api:ReturnType<typeof useDrag>
let dropZoneEl:HTMLDivElement
let dropHandler:ReturnType<typeof vi.fn>
beforeEach(()=>{
dropZoneEl=document.createElement('div')
Object.defineProperty(dropZoneEl,'getBoundingClientRect',{value:()=>({left:0,right:100,top:0,bottom:100})})
document.body.appendChild(dropZoneEl)
dropHandler=vi.fn()
render(<DragProvider><TestConsumer onMount={(a)=>{api=a}}/></DragProvider>)
})
it('clears drag data after successful drop inside zone',()=>{
//Setup: register drop zone and set drag data
api.registerDropZone('test-zone',dropZoneEl,dropHandler)
act(()=>{api.setDragData({type:'asset',path:'/test/image.png'})})
expect(api.getDragData()).not.toBeNull()
//Simulate mouseup inside drop zone
const mouseUpEvent=new MouseEvent('mouseup',{clientX:50,clientY:50,bubbles:true})
act(()=>{document.dispatchEvent(mouseUpEvent)})
//Verify handler called and drag data cleared
expect(dropHandler).toHaveBeenCalledTimes(1)
expect(dropHandler).toHaveBeenCalledWith({type:'asset',path:'/test/image.png'})
expect(api.getDragData()).toBeNull()
expect(api.dragData).toBeNull()
})
it('clears drag data after mouseup outside drop zone',()=>{
api.registerDropZone('test-zone',dropZoneEl,dropHandler)
act(()=>{api.setDragData({type:'asset',path:'/test/image.png'})})
//Simulate mouseup outside drop zone (x=200, outside 0-100 range)
const mouseUpEvent=new MouseEvent('mouseup',{clientX:200,clientY:200,bubbles:true})
act(()=>{document.dispatchEvent(mouseUpEvent)})
//Verify handler NOT called but drag data still cleared
expect(dropHandler).not.toHaveBeenCalled()
expect(api.getDragData()).toBeNull()
})
it('does not duplicate on subsequent clicks after drop (regression test)',()=>{
//This tests the exact bug that was fixed: after a drop, clicking again
//should NOT trigger another drop because drag data should be cleared
api.registerDropZone('test-zone',dropZoneEl,dropHandler)
act(()=>{api.setDragData({type:'asset',path:'/test/image.png'})})
//First mouseup - should trigger drop
const firstMouseUp=new MouseEvent('mouseup',{clientX:50,clientY:50,bubbles:true})
act(()=>{document.dispatchEvent(firstMouseUp)})
expect(dropHandler).toHaveBeenCalledTimes(1)
//Second mouseup (simulating a click) - should NOT trigger drop again
const secondMouseUp=new MouseEvent('mouseup',{clientX:50,clientY:50,bubbles:true})
act(()=>{document.dispatchEvent(secondMouseUp)})
//CRITICAL: handler should still only have been called once
expect(dropHandler).toHaveBeenCalledTimes(1)
})
it('handles multiple drop zones correctly',()=>{
const secondZone=document.createElement('div')
Object.defineProperty(secondZone,'getBoundingClientRect',{value:()=>({left:200,right:300,top:0,bottom:100})})
const secondHandler=vi.fn()
api.registerDropZone('zone-1',dropZoneEl,dropHandler)
api.registerDropZone('zone-2',secondZone,secondHandler)
act(()=>{api.setDragData({type:'template',path:'my-template'})})
//Drop in second zone
const mouseUp=new MouseEvent('mouseup',{clientX:250,clientY:50,bubbles:true})
act(()=>{document.dispatchEvent(mouseUp)})
expect(dropHandler).not.toHaveBeenCalled()
expect(secondHandler).toHaveBeenCalledTimes(1)
expect(api.getDragData()).toBeNull()
})
it('unregisters drop zones correctly',()=>{
api.registerDropZone('test-zone',dropZoneEl,dropHandler)
api.unregisterDropZone('test-zone')
act(()=>{api.setDragData({type:'asset',path:'/test/image.png'})})
const mouseUp=new MouseEvent('mouseup',{clientX:50,clientY:50,bubbles:true})
act(()=>{document.dispatchEvent(mouseUp)})
//Handler should not be called since zone was unregistered
expect(dropHandler).not.toHaveBeenCalled()
//But drag data should still be cleared
expect(api.getDragData()).toBeNull()
})
it('adds and removes is-dragging class on body',()=>{
expect(document.body.classList.contains('is-dragging')).toBe(false)
act(()=>{api.setDragData({type:'product',path:'product-slug'})})
expect(document.body.classList.contains('is-dragging')).toBe(true)
act(()=>{api.clearDrag()})
expect(document.body.classList.contains('is-dragging')).toBe(false)
})
})
