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

export class Cube3D {
  constructor(canvas, mapping) {
    this.canvas  = canvas;
    this.mapping = mapping.mapping;  // [[x,y], ...]
    this.width   = mapping.width;    // 32
    this.height  = mapping.height;   // 15
    this.LEDS    = 480;

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
    this.camera.position.set(3.5, 2.5, 3.5);
    this.camera.lookAt(0, 0, 0);

    this.controls = new OrbitControls(this.camera, this.canvas);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.minDistance   = 2;
    this.controls.maxDistance   = 10;

    // Ambient light für leichte Aufhellung
    this.scene.add(new THREE.AmbientLight(0xffffff, 0.3));

    window.addEventListener('resize', () => this._onResize());
  }

  _initCube() {
    // 6 Canvas-Texturen, eine pro Fläche
    this.ctxs      = [];
    this.textures  = [];
    const materials = [];

    for (let i = 0; i < 6; i++) {
      const cv  = document.createElement('canvas');
      cv.width  = this.width;
      cv.height = this.height;
      const ctx = cv.getContext('2d');
      ctx.fillStyle = '#000';
      ctx.fillRect(0, 0, this.width, this.height);
      this.ctxs.push(ctx);

      const tex = new THREE.CanvasTexture(cv);
      tex.magFilter = THREE.NearestFilter;
      tex.minFilter = THREE.NearestFilter;
      this.textures.push(tex);
    }

    // BoxGeometry erwartet Materialien in der Reihenfolge +X,-X,+Y,-Y,+Z,-Z
    for (let matIdx = 0; matIdx < 6; matIdx++) {
      const faceIdx = FACE_MATERIAL_ORDER[matIdx];
      materials.push(new THREE.MeshBasicMaterial({
        map:  this.textures[faceIdx],
        side: THREE.FrontSide,
      }));
    }

    const geo  = new THREE.BoxGeometry(2, 2, 2);
    this.mesh  = new THREE.Mesh(geo, materials);
    this.scene.add(this.mesh);
  }

  /**
   * Verarbeitet einen binären WebSocket-Frame (8640 Bytes).
   * Layout: face0[1440] face1[1440] ... face5[1440]
   * Pro Face: vled0[RGB] vled1[RGB] ... vled479[RGB]
   */
  updateFrame(buffer) {
    const bytes = new Uint8Array(buffer);
    const ledsPerFace = this.LEDS;

    for (let face = 0; face < 6; face++) {
      const ctx    = this.ctxs[face];
      const offset = face * ledsPerFace * 3;
      const imgData = ctx.getImageData(0, 0, this.width, this.height);
      const data    = imgData.data;

      for (let vled = 0; vled < ledsPerFace; vled++) {
        const [x, y] = this.mapping[vled];
        const si = offset + vled * 3;
        const di = (y * this.width + x) * 4;
        data[di]     = bytes[si];
        data[di + 1] = bytes[si + 1];
        data[di + 2] = bytes[si + 2];
        data[di + 3] = 255;
      }

      ctx.putImageData(imgData, 0, 0);
      this.textures[face].needsUpdate = true;
    }
  }

  _animate() {
    requestAnimationFrame(() => this._animate());
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
