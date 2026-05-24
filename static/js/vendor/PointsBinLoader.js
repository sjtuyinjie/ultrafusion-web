import {
	BufferGeometry,
	FileLoader,
	Float32BufferAttribute,
	Loader
} from './three.module.js';

const MAGIC_V1 = 'UFPC1';
const MAGIC_V2 = 'UFPC2';
const HEADER_V2 = 9;

class PointsBinLoader extends Loader {

	load(url, onLoad, onProgress, onError) {
		const scope = this;
		const loader = new FileLoader(this.manager);
		loader.setPath(this.path);
		loader.setResponseType('arraybuffer');
		loader.setRequestHeader(this.requestHeader);
		loader.setWithCredentials(this.withCredentials);
		loader.load(
			url,
			function(buffer) {
				try {
					onLoad(scope.parse(buffer));
				} catch (error) {
					if (onError) {
						onError(error);
					} else {
						console.error(error);
					}
					scope.manager.itemError(url);
				}
			},
			onProgress,
			onError
		);
	}

	copyFloat32Range(buffer, byteOffset, floatCount) {
		const byteLength = floatCount * 4;
		return new Float32Array(buffer.slice(byteOffset, byteOffset + byteLength));
	}

	parse(buffer) {
		const bytes = new Uint8Array(buffer);
		if (bytes.length < HEADER_V2) {
			throw new Error('Point cloud cache file is too small.');
		}

		const magic = String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3], bytes[4]);
		const view = new DataView(buffer);
		const count = view.getUint32(5, true);

		if (magic === MAGIC_V2) {
			const positionsOffset = HEADER_V2;
			const colorsOffset = positionsOffset + count * 12;
			const expectedSize = colorsOffset + count * 3;
			if (bytes.length < expectedSize) {
				throw new Error('Point cloud cache is truncated.');
			}

			const positions = this.copyFloat32Range(buffer, positionsOffset, count * 3);
			const colorBytes = new Uint8Array(buffer, colorsOffset, count * 3);
			const colors = new Float32Array(count * 3);
			const inv = 1 / 255;
			for (let i = 0, len = colorBytes.length; i < len; i++) {
				colors[i] = colorBytes[i] * inv;
			}

			const geometry = new BufferGeometry();
			geometry.setAttribute('position', new Float32BufferAttribute(positions, 3));
			geometry.setAttribute('color', new Float32BufferAttribute(colors, 3));
			geometry.computeBoundingSphere();
			return geometry;
		}

		if (magic !== MAGIC_V1) {
			throw new Error('Invalid point cloud cache (expected ' + MAGIC_V2 + ').');
		}

		const expectedSize = HEADER_V2 + count * 15;
		if (bytes.length < expectedSize) {
			throw new Error('Point cloud cache is truncated.');
		}

		const positions = new Float32Array(count * 3);
		const colors = new Float32Array(count * 3);
		let offset = HEADER_V2;

		for (let i = 0; i < count; i++) {
			const x = view.getFloat32(offset, true);
			offset += 4;
			const y = view.getFloat32(offset, true);
			offset += 4;
			const z = view.getFloat32(offset, true);
			offset += 4;
			const r = bytes[offset++];
			const g = bytes[offset++];
			const b = bytes[offset++];

			const idx = i * 3;
			positions[idx] = x;
			positions[idx + 1] = y;
			positions[idx + 2] = z;
			colors[idx] = r / 255;
			colors[idx + 1] = g / 255;
			colors[idx + 2] = b / 255;
		}

		const geometry = new BufferGeometry();
		geometry.setAttribute('position', new Float32BufferAttribute(positions, 3));
		geometry.setAttribute('color', new Float32BufferAttribute(colors, 3));
		geometry.computeBoundingSphere();
		return geometry;
	}

}

export { PointsBinLoader };
