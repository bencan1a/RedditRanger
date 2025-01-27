import svgwrite
from svgwrite import path

def create_fremen_snoo(filename="static/fremen_snoo.svg", size=400):
    # Create SVG document
    dwg = svgwrite.Drawing(filename, size=(size, size))
    
    # Define colors
    stillsuit_color = "#2B2B2B"
    eye_color = "#0077FF"  # Bright blue for spice eyes
    skin_color = "#FFFFFF"
    
    # Create base group with centered coordinates
    center_x = size / 2
    center_y = size / 2
    g = dwg.g(transform=f"translate({center_x},{center_y})")
    
    # Head (slightly smaller for stillsuit hood)
    head_size = size * 0.35
    g.add(dwg.circle(center=(0, 0), r=head_size, 
                     fill=stillsuit_color))
    
    # Stillsuit hood details
    hood = path.Path(fill=stillsuit_color, stroke="#404040", stroke_width=2)
    hood.push(f"M {-head_size*0.8} {head_size*0.5}")
    hood.push(f"Q {-head_size*0.4} {head_size*0.8} 0 {head_size*0.5}")
    hood.push(f"Q {head_size*0.4} {head_size*0.8} {head_size*0.8} {head_size*0.5}")
    hood.push(f"L {head_size*0.8} {-head_size*0.3}")
    hood.push(f"Q {head_size*0.4} {-head_size*0.6} 0 {-head_size*0.5}")
    hood.push(f"Q {-head_size*0.4} {-head_size*0.6} {-head_size*0.8} {-head_size*0.3}")
    hood.push("Z")
    g.add(hood)
    
    # Spice-blue eyes
    eye_size = size * 0.05
    eye_spacing = size * 0.12
    # Left eye
    g.add(dwg.circle(center=(-eye_spacing, -size*0.05), r=eye_size, 
                     fill=eye_color, filter="url(#glow)"))
    # Right eye
    g.add(dwg.circle(center=(eye_spacing, -size*0.05), r=eye_size, 
                     fill=eye_color, filter="url(#glow)"))
    
    # Add glow filter for the eyes
    glow = dwg.filter(id="glow")
    glow.feGaussianBlur(in_="SourceGraphic", stdDeviation="2")
    dwg.defs.add(glow)
    
    # Breathing apparatus / dust mask
    mask = path.Path(fill="#404040", stroke="#333333", stroke_width=2)
    mask.push(f"M {-head_size*0.4} {size*0.05}")
    mask.push(f"Q {-head_size*0.2} {size*0.15} 0 {size*0.05}")
    mask.push(f"Q {head_size*0.2} {size*0.15} {head_size*0.4} {size*0.05}")
    mask.push(f"Q {head_size*0.2} {-size*0.05} 0 {-size*0.05}")
    mask.push(f"Q {-head_size*0.2} {-size*0.05} {-head_size*0.4} {size*0.05}")
    g.add(mask)
    
    # Add breathing tubes
    tube_left = path.Path(fill="none", stroke="#333333", stroke_width=3)
    tube_left.push(f"M {-head_size*0.3} {size*0.05}")
    tube_left.push(f"Q {-head_size*0.4} {size*0.2} {-head_size*0.35} {size*0.25}")
    g.add(tube_left)
    
    tube_right = path.Path(fill="none", stroke="#333333", stroke_width=3)
    tube_right.push(f"M {head_size*0.3} {size*0.05}")
    tube_right.push(f"Q {head_size*0.4} {size*0.2} {head_size*0.35} {size*0.25}")
    g.add(tube_right)
    
    # Add the group to the drawing
    dwg.add(g)
    
    # Save the SVG
    dwg.save()
    return filename

if __name__ == "__main__":
    # Create the Fremen Snoo
    icon_path = create_fremen_snoo()
    print(f"Created Fremen Snoo icon at: {icon_path}")
