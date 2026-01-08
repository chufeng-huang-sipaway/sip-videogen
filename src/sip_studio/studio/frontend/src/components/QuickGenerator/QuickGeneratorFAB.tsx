//Floating action button for quick image generation
interface Props{onClick:()=>void;disabled?:boolean}
export function QuickGeneratorFAB({onClick,disabled}:Props){
return(<button className="quick-generator-fab" onClick={onClick} disabled={disabled} title="Quick Image Generator"><span className="fab-icon">+</span></button>)}
