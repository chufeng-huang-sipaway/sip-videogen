import{describe,it,expect,vi,beforeEach}from'vitest'
import{renderHook,act,waitFor}from'@testing-library/react'
import{useChat}from'../useChat'
import{DEFAULT_ASPECT_RATIO,DEFAULT_GENERATION_MODE}from'@/types/aspectRatio'
//Mock bridge module
const mockChat=vi.fn()
const mockClearChat=vi.fn().mockResolvedValue(undefined)
const mockGetProgress=vi.fn().mockResolvedValue({})
let mockIsPyWebView=false
vi.mock('@/lib/bridge',()=>({bridge:{chat:(...args:any[])=>mockChat(...args),clearChat:(...args:any[])=>mockClearChat(...args),getProgress:(...args:any[])=>mockGetProgress(...args)},isPyWebView:()=>mockIsPyWebView}))
describe('useChat brand isolation',()=>{
  beforeEach(()=>{vi.clearAllMocks();mockIsPyWebView=false})
  it('ignores in-flight responses after brand change',async()=>{
    let resolveChat:(v:any)=>void=()=>{}
    mockChat.mockImplementation(()=>new Promise(r=>{resolveChat=r}))
    mockIsPyWebView=true
    const{result,rerender}=renderHook(({brand})=>useChat(brand),{initialProps:{brand:'brand-a'}})
    //Start request on brand-a
    await act(async()=>{result.current.sendMessage('test',{})})
    expect(result.current.isLoading).toBe(true)
    //Switch to brand-b before response
    rerender({brand:'brand-b'})
    expect(result.current.messages).toHaveLength(0)
    expect(result.current.isLoading).toBe(false)
    //Late response arrives - should be ignored
    await act(async()=>{resolveChat({response:'late',images:[]})})
    //Wait a tick for any potential state updates
    await waitFor(()=>{expect(result.current.messages).toHaveLength(0)})
  })
  it('resets generation settings on brand change',async()=>{
    const{result,rerender}=renderHook(({brand})=>useChat(brand),{initialProps:{brand:'brand-a'}})
    //Change settings to non-default values
    act(()=>{result.current.setAspectRatio('1:1');result.current.setGenerationMode('video')})
    expect(result.current.aspectRatio).toBe('1:1')
    expect(result.current.generationMode).toBe('video')
    //Switch brand
    rerender({brand:'brand-b'})
    //Settings should reset to defaults
    expect(result.current.aspectRatio).toBe(DEFAULT_ASPECT_RATIO)
    expect(result.current.generationMode).toBe(DEFAULT_GENERATION_MODE)
  })
})
