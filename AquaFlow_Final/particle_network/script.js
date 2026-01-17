/**
 * Particle Network Animation
 * Features:
 * - Responsive canvas
 * - Particle system with random movement and bounce
 * - Dynamic network connections based on distance
 * - Mouse interaction (attraction/repulsion)
 */

const canvas = document.getElementById('particleNet');
const ctx = canvas.getContext('2d');

let width, height;
let particles = [];

// Configuration
const config = {
    particleColor: 'rgba(102, 126, 234, 0.7)',
    lineColor: 'rgba(102, 126, 234,', // Opacity will be dynamic
    particleAmount: 0, // Will be calculated based on screen size
    defaultSpeed: 1,
    variantSpeed: 1,
    linkRadius: 150, // Distance to connect particles
    mouseRadius: 200, // Distance for mouse interaction
    mouseForce: 0.05 // Strength of mouse attraction
};

// Mouse state
let mouse = {
    x: null,
    y: null
};

// Particle Class
class Particle {
    constructor() {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        this.vx = (Math.random() - 0.5) * config.defaultSpeed;
        this.vy = (Math.random() - 0.5) * config.defaultSpeed;
        this.size = Math.random() * 2 + 1; // Size between 1 and 3
    }

    update() {
        // Simple movement
        this.x += this.vx;
        this.y += this.vy;

        // Bounce off edges
        if (this.x < 0 || this.x > width) {
            this.vx *= -1;
        }
        if (this.y < 0 || this.y > height) {
            this.vy *= -1;
        }

        // Mouse interaction
        // If mouse is within canvas
        if (mouse.x != null) {
            let dx = mouse.x - this.x;
            let dy = mouse.y - this.y;
            let distance = Math.sqrt(dx * dx + dy * dy);

            if (distance < config.mouseRadius) {
                // Determine direction to mouse
                const forceDirectionX = dx / distance;
                const forceDirectionY = dy / distance;

                // Calculate force magnitude (stronger when closer)
                const force = (config.mouseRadius - distance) / config.mouseRadius;

                // Choose attraction (+) or repulsion (-)
                // Let's do attraction for a "constellation" feel, but gently
                // Or maybe a slight repulsion creates a cool "interactive displacement"
                // The prompt asked for "gently attracted to (or repelled)"
                // Let's do Gentle Attraction
                const directionX = forceDirectionX * force * config.mouseForce;
                const directionY = forceDirectionY * force * config.mouseForce;

                this.vx += directionX;
                this.vy += directionY;
            }
        }
    }

    draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fillStyle = config.particleColor;
        ctx.fill();
    }
}

// Initialize Canvas
function init() {
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = width;
    canvas.height = height;

    // Calculate number of particles based on area
    // e.g., one particle per 9000 pixels
    const area = width * height;
    config.particleAmount = Math.floor(area / 9000);

    createParticles();
}

function createParticles() {
    particles = [];
    for (let i = 0; i < config.particleAmount; i++) {
        particles.push(new Particle());
    }
}

// Animation Loop
function animate() {
    requestAnimationFrame(animate);
    ctx.clearRect(0, 0, width, height);

    for (let i = 0; i < particles.length; i++) {
        particles[i].update();
        particles[i].draw();
    }

    connectParticles();
}

// Draw lines between particles
function connectParticles() {
    let opacityValue = 1;
    for (let a = 0; a < particles.length; a++) {
        for (let b = a + 1; b < particles.length; b++) {

            let distance = ((particles[a].x - particles[b].x) * (particles[a].x - particles[b].x)) +
                ((particles[a].y - particles[b].y) * (particles[a].y - particles[b].y));

            // Optimization: compare squared distance to avoid sqrt in inner loop
            if (distance < (config.linkRadius * config.linkRadius)) {
                opacityValue = 1 - (distance / (20000)); // Rough estimation for fading

                // More precise opacity calculation:
                // opacity = 1 - (Math.sqrt(distance) / config.linkRadius)
                // But let's keep it performant. 
                // Let's use the actual distance for opacity calc if we want it smooth
                let dist = Math.sqrt(distance);
                opacityValue = 1 - (dist / config.linkRadius);

                if (opacityValue > 0) {
                    ctx.strokeStyle = config.lineColor + opacityValue + ')';
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(particles[a].x, particles[a].y);
                    ctx.lineTo(particles[b].x, particles[b].y);
                    ctx.stroke();
                }
            }
        }
    }
}

// Event Listeners
window.addEventListener('resize', () => {
    init(); // Re-initialize on resize
});

window.addEventListener('mousemove', (e) => {
    mouse.x = e.x;
    mouse.y = e.y;
});

window.addEventListener('mouseout', () => {
    mouse.x = null;
    mouse.y = null;
});

// Start
init();
animate();
