/**
 * 3D-Würfelvorschau via Three.js.
 *
 * Three.js BoxGeometry Material-Reihenfolge: +X,-X,+Y,-Y,+Z,-Z
 * Unsere Faces: 0=FRONT,1=BACK,2=LEFT,3=RIGHT,4=TOP,5=BOTTOM
 * Mapping: materials[0]=RIGHT(3), [1]=LEFT(2), [2]=TOP(4),
 *          [3]=BOTTOM(5), [4]=FRONT(0), [5]=BACK(1)
 */
import * as THREE from '/ui/js/vendor/three.module.min.js';
import { OrbitControls } from '/ui/js/vendor/OrbitControls.js';

const FACE_MATERIAL_ORDER = [3, 2, 4, 5, 0, 1];

// Jede LED wird als SCALE×SCALE Block gerendert (1px Abstand)
const SCALE = 10;

export class Cube3D {
  constructor(canvas, mapping) {
    this.canvas  = canvas;
    this.mapping = mapping.mapping;  // [[x,y], ...]
    this.width   = mapping.width;    // 32
    this.height  = mapping.height;   // 15
    this.LEDS    = 480;

    // Letzter empfangener WS-Frame — wird im RAF-Loop verarbeitet
    this._pendingFrame = null;

    this._initThree();
    this._initCube();
    this._animate();
  }

  _initThree() {
    const { clientWidth: w, clientHeight: h } = this.canvas;
    this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.setSize(w, h);

    this.scene  = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);

    // Kamera: niedrige Elevation → Würfel erscheint als hängende Raute
    this.camera.position.set(3.5, 1.2, 3.5);
    this.camera.lookAt(0, 0, 0);

    this.controls = new OrbitControls(this.camera, this.canvas);
    this.controls.enableDamping  = true;
    this.controls.dampingFactor  = 0.08;
    this.controls.minDistance    = 2;
    this.controls.maxDistance    = 10;
    this.controls.target.set(0, 0, 0);

    // Polaren Winkel fixieren → Ecke bleibt oben, nur horizontale Drehung erlaubt
    const camDist    = Math.sqrt(3.5 * 3.5 + 1.2 * 1.2 + 3.5 * 3.5);
    const polarAngle = Math.acos(1.2 / camDist);
    this.controls.minPolarAngle = polarAngle;
    this.controls.maxPolarAngle = polarAngle;

    window.addEventListener('resize', () => this._onResize());
  }

  _initCube() {
    const texW = this.width  * SCALE;   // 320
    const texH = this.height * SCALE;   // 150

    // Pro Fläche: RGBA-Puffer direkt im Speicher — keine Canvas-Umwege
    this.pixelBufs = Array.from({ length: 6 }, () => {
      const buf = new Uint8Array(texW * texH * 4);
      // Alpha fest auf 255
      for (let i = 3; i < buf.length; i += 4) buf[i] = 255;
      return buf;
    });

    this.textures  = [];
    const materials = [];

    for (let i = 0; i < 6; i++) {
      // DataTexture: Three.js liest direkt aus pixelBufs[i]
      const tex = new THREE.DataTexture(this.pixelBufs[i], texW, texH, THREE.RGBAFormat);
      tex.magFilter  = THREE.LinearFilter;
      tex.minFilter  = THREE.LinearFilter;
      tex.flipY      = true;
      tex.needsUpdate = true;
      this.textures.push(tex);
    }

    for (let matIdx = 0; matIdx < 6; matIdx++) {
      const faceIdx = FACE_MATERIAL_ORDER[matIdx];
      materials.push(new THREE.MeshBasicMaterial({
        map:  this.textures[faceIdx],
        side: THREE.FrontSide,
      }));
    }

    const geo = new THREE.BoxGeometry(2, 2, 2);
    this.mesh = new THREE.Mesh(geo, materials);

    // Würfel an einer Ecke hängend:
    // Ecke (1,1,1) exakt nach oben (Welt-Y) ausrichten — via Quaternion, kein Euler-Gimbal
    const q1 = new THREE.Quaternion().setFromUnitVectors(
      new THREE.Vector3(1, 1, 1).normalize(),
      new THREE.Vector3(0, 1, 0)
    );
    // +30° um Welt-Y → symmetric 3-Flächen-Ansicht von vorne
    const q2 = new THREE.Quaternion().setFromAxisAngle(
      new THREE.Vector3(0, 1, 0), Math.PI / 6
    );
    this.mesh.quaternion.multiplyQuaternions(q2, q1);

    this.scene.add(this.mesh);
  }

  /**
   * Wird vom WebSocket-Handler aufgerufen.
   * Speichert nur eine Referenz — Rendering passiert im RAF-Loop.
   */
  setFrame(buffer) {
    this._pendingFrame = buffer;
    this._framesReceived = (this._framesReceived || 0) + 1;
  }

  /** Pixel-Buffer aktualisieren: läuft im RAF-Loop, direkt vor dem Render. */
  _applyFrame(buffer) {
    const bytes       = new Uint8Array(buffer);
    const texW        = this.width  * SCALE;
    const ledsPerFace = this.LEDS;
    const S           = SCALE - 1;   // Blockgröße (1px Lücke)

    for (let face = 0; face < 6; face++) {
      const buf    = this.pixelBufs[face];
      const offset = face * ledsPerFace * 3;

      // RGB auf Schwarz setzen (Alpha = 255 bleibt unberührt)
      for (let i = 0; i < buf.length; i += 4) {
        buf[i] = buf[i + 1] = buf[i + 2] = 0;
      }

      for (let vled = 0; vled < ledsPerFace; vled++) {
        const [x, y] = this.mapping[vled];
        const si = offset + vled * 3;
        const r  = bytes[si];
        const g  = bytes[si + 1];
        const b  = bytes[si + 2];

        const px0 = x * SCALE;
        const py0 = y * SCALE;

        for (let dy = 0; dy < S; dy++) {
          const rowBase = (py0 + dy) * texW;
          for (let dx = 0; dx < S; dx++) {
            const di = (rowBase + px0 + dx) * 4;
            buf[di]     = r;
            buf[di + 1] = g;
            buf[di + 2] = b;
          }
        }
      }

      this.textures[face].needsUpdate = true;
    }
  }

  _animate() {
    requestAnimationFrame(() => this._animate());

    if (this._pendingFrame) {
      this._applyFrame(this._pendingFrame);
      this._pendingFrame = null;
    }

    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  _onResize() {
    const { clientWidth: w, clientHeight: h } = this.canvas;
    if (w === 0 || h === 0) return;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }
}
