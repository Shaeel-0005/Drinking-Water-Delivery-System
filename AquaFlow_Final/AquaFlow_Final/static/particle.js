/**
 * Premium Aqua Flow Animation v3
 * Features:
 * - Rising bubbles with enhanced specular highlights
 * - Floating 3D-style water bottles (Reduced density)
 * - Interactive fluid movement
 */

document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('particleNet');
    if (!canvas) {
        console.error('Particle canvas not found');
        return;
    }
    const ctx = canvas.getContext('2d');

    let width, height;
    let particles = [];
    let bottles = [];

    // Configuration
    const config = {
        bubbleBaseColor: 'rgba(255, 255, 255, 0.1)',
        bubbleShineColor: 'rgba(255, 255, 255, 0.6)',
        bottleColor: 'rgba(200, 230, 255, 0.3)',
        bottleCapColor: '#0284c7', // Sky 600
        particleAmount: 0,
        bottleAmount: 0,
        mouseRadius: 200,
        mouseForce: 3
    };

    // Mouse state
    let mouse = { x: null, y: null };

    // --- Utility Classes ---

    class Particle {
        constructor() {
            this.init(true);
        }

        init(randomY = false) {
            this.x = Math.random() * width;
            this.y = randomY ? Math.random() * height : height + 20;
            this.vy = -(Math.random() * 2.0 + 0.5); // Faster rise
            this.size = Math.random() * 10 + 3; // 3 to 13px
            this.wobbleOffset = Math.random() * Math.PI * 2;
            this.alpha = Math.random() * 0.2 + 0.1;
        }

        update() {
            this.y += this.vy;
            this.x += Math.sin(this.y * 0.015 + this.wobbleOffset) * 1.5; // More wobble

            // Mouse Repulsion
            if (mouse.x != null) {
                let dx = mouse.x - this.x;
                let dy = mouse.y - this.y;
                let distance = Math.sqrt(dx * dx + dy * dy);
                if (distance < config.mouseRadius) {
                    const force = (config.mouseRadius - distance) / config.mouseRadius;
                    this.x -= (dx / distance) * force * config.mouseForce;
                    this.y -= (dy / distance) * force * config.mouseForce;
                }
            }

            if (this.y < -this.size * 2) this.init(false);
        }

        draw() {
            ctx.save();
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255, 255, 255, ${this.alpha})`;
            ctx.fill();

            // Specular Highlight
            ctx.beginPath();
            ctx.arc(this.x - this.size * 0.3, this.y - this.size * 0.3, this.size * 0.2, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255, 255, 255, ${this.alpha + 0.4})`;
            ctx.fill();
            ctx.restore();
        }
    }

    class Bottle {
        constructor() {
            this.init(true);
        }

        init(randomY = false) {
            this.x = Math.random() * width;
            this.y = randomY ? Math.random() * height : height + 100;
            this.vy = -(Math.random() * 1.0 + 0.3);
            this.width = Math.random() * 15 + 15; // Smaller bottles
            this.height = this.width * 2.8;
            this.angle = Math.random() * Math.PI * 2;
            this.rotationSpeed = (Math.random() - 0.5) * 0.03;
            this.alpha = Math.random() * 0.2 + 0.15;
        }

        update() {
            this.y += this.vy;
            this.angle += this.rotationSpeed;

            if (mouse.x != null) {
                let dx = mouse.x - this.x;
                let dy = mouse.y - this.y;
                let distance = Math.sqrt(dx * dx + dy * dy);
                if (distance < config.mouseRadius) {
                    const force = (config.mouseRadius - distance) / config.mouseRadius;
                    this.x -= (dx / distance) * force * config.mouseForce * 0.6;
                    this.y -= (dy / distance) * force * config.mouseForce * 0.6;
                }
            }

            if (this.y < -this.height * 2) this.init(false);
        }

        draw() {
            ctx.save();
            ctx.translate(this.x, this.y);
            ctx.rotate(this.angle);

            // Bottle Body
            const w = this.width;
            const h = this.height;
            const r = w * 0.2;

            ctx.beginPath();
            ctx.roundRect(-w / 2, -h / 2, w, h, r);
            ctx.fillStyle = `rgba(224, 242, 254, ${this.alpha})`;
            ctx.fill();
            ctx.strokeStyle = `rgba(255, 255, 255, ${this.alpha + 0.2})`;
            ctx.lineWidth = 1.5;
            ctx.stroke();

            // Water
            ctx.beginPath();
            ctx.roundRect(-w / 2 + 2, 0, w - 4, h / 2 - 2, [0, 0, r - 2, r - 2]);
            ctx.fillStyle = `rgba(56, 189, 248, ${this.alpha * 0.9})`; // Sky 400
            ctx.fill();

            // Cap
            ctx.fillStyle = config.bottleCapColor;
            ctx.beginPath();
            ctx.roundRect(-w * 0.3, -h / 2 - h * 0.1, w * 0.6, h * 0.1, 2);
            ctx.fill();

            // White Label (Restoring requested feature)
            ctx.fillStyle = `rgba(255, 255, 255, ${this.alpha + 0.5})`;
            ctx.beginPath();
            ctx.rect(-w / 2 + 1, -h * 0.1, w - 2, h * 0.25);
            ctx.fill();

            // Label Accent Line
            ctx.fillStyle = `rgba(2, 132, 199, ${this.alpha})`;
            ctx.beginPath();
            ctx.rect(-w * 0.2, -h * 0.02, w * 0.4, 2);
            ctx.fill();

            ctx.restore();
        }
    }

    // --- Main Logic ---

    function init() {
        width = window.innerWidth;
        height = window.innerHeight;
        canvas.width = width;
        canvas.height = height;

        const area = width * height;
        // BALANCED DENSITY
        config.particleAmount = Math.floor(area / 10000); // Bubbles
        config.bottleAmount = Math.floor(area / 100000);  // Bottles

        createElements();
    }

    function createElements() {
        particles = [];
        bottles = [];
        for (let i = 0; i < config.particleAmount; i++) particles.push(new Particle());
        for (let i = 0; i < config.bottleAmount; i++) bottles.push(new Bottle());
    }

    function animate() {
        requestAnimationFrame(animate);
        ctx.clearRect(0, 0, width, height);

        // Draw Order: Bottles -> Bubbles
        bottles.forEach(b => { b.update(); b.draw(); });
        particles.forEach(p => { p.update(); p.draw(); });
    }

    // Event Listeners
    window.addEventListener('resize', init);
    window.addEventListener('mousemove', e => {
        mouse.x = e.clientX;
        mouse.y = e.clientY;
    });
    window.addEventListener('mouseout', () => {
        mouse.x = null;
        mouse.y = null;
    });

    init();
    animate();
});
