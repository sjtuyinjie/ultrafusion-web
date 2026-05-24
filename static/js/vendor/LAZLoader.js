import {
	BufferGeometry,
	FileLoader,
	Float32BufferAttribute,
	Loader
} from './three.module.js';

const LOADERS_CDN_SOURCES = [
	[
		'https://cdn.jsdelivr.net/npm/@loaders.gl/core@4.3.3/+esm',
		'https://cdn.jsdelivr.net/npm/@loaders.gl/las@4.3.3/+esm'
	],
	[
		'https://esm.sh/@loaders.gl/core@4.3.3',
		'https://esm.sh/@loaders.gl/las@4.3.3'
	]
];
const LOADERS_IMPORT_TIMEOUT_MS = 20000;

let loadersPromise = null;

function importWithTimeout(url, timeoutMs) {
	return Promise.race([
		import(url),
		new Promise(function(_, reject) {
			setTimeout(function() {
				reject(new Error('Timed out loading ' + url));
			}, timeoutMs);
		})
	]);
}

function getLoaders() {
	if (!loadersPromise) {
		loadersPromise = (async function() {
			var lastError = null;

			for (var i = 0; i < LOADERS_CDN_SOURCES.length; i++) {
				var sources = LOADERS_CDN_SOURCES[i];
				try {
					var modules = await Promise.all(sources.map(function(url) {
						return importWithTimeout(url, LOADERS_IMPORT_TIMEOUT_MS);
					}));
					return {
						load: modules[0].load,
						LASLoader: modules[1].LASLoader
					};
				} catch (error) {
					lastError = error;
					console.warn('LAZ decoder CDN failed:', sources[0], error);
				}
			}

			throw lastError || new Error('Failed to load LAZ/LAS decoder modules.');
		})();
	}
	return loadersPromise;
}

function clamp01(value) {
	return Math.max(0, Math.min(1, value));
}

function setGeometryColors(geometry, attributes) {
	// Colors exported from SuperSplat are linear RGB stored as 8-bit (or 16-bit in LAS).
	var colorAttr = attributes.COLOR_0;
	if (colorAttr && colorAttr.value) {
		var values = colorAttr.value;
		var itemSize = colorAttr.size || 3;
		var count = Math.floor(values.length / itemSize);
		var colors = new Float32Array(count * 3);
		var divisor = values.some(function(v) { return v > 1; }) ? 255 : 1;

		for (var i = 0; i < count; i++) {
			var base = i * itemSize;
			colors[i * 3] = clamp01(values[base] / divisor);
			colors[i * 3 + 1] = clamp01(values[base + 1] / divisor);
			colors[i * 3 + 2] = clamp01(values[base + 2] / divisor);
		}

		geometry.setAttribute('color', new Float32BufferAttribute(colors, 3));
		return;
	}

	var red = attributes.RED;
	var green = attributes.GREEN;
	var blue = attributes.BLUE;
	if (red && green && blue && red.value && green.value && blue.value) {
		var n = red.value.length;
		var rgb = new Float32Array(n * 3);
		var divisor = red.value.some(function(v) { return v > 255; }) ? 65535 : 255;

		for (var j = 0; j < n; j++) {
			rgb[j * 3] = clamp01(red.value[j] / divisor);
			rgb[j * 3 + 1] = clamp01(green.value[j] / divisor);
			rgb[j * 3 + 2] = clamp01(blue.value[j] / divisor);
		}

		geometry.setAttribute('color', new Float32BufferAttribute(rgb, 3));
	}
}

function meshToGeometry(mesh) {
	var geometry = new BufferGeometry();
	var position = mesh.attributes.POSITION;

	if (!position || !position.value) {
		throw new Error('LAZ/LAS file does not contain POSITION data.');
	}

	geometry.setAttribute('position', new Float32BufferAttribute(position.value, 3));
	setGeometryColors(geometry, mesh.attributes);
	geometry.computeBoundingSphere();
	return geometry;
}

class LAZLoader extends Loader {

	constructor(manager) {
		super(manager);
		this.skip = 1;
	}

	load(url, onLoad, onProgress, onError) {
		var scope = this;
		var loader = new FileLoader(this.manager);
		loader.setPath(this.path);
		loader.setResponseType('arraybuffer');
		loader.setRequestHeader(this.requestHeader);
		loader.setWithCredentials(this.withCredentials);
		loader.load(
			url,
			function(buffer) {
				scope.parse(buffer).then(onLoad).catch(function(error) {
					if (onError) {
						onError(error);
					} else {
						console.error(error);
					}
					scope.manager.itemError(url);
				});
			},
			onProgress,
			onError
		);
	}

	async parse(buffer) {
		var loaders = await getLoaders();
		var mesh = await loaders.load(buffer, loaders.LASLoader, {
			las: {
				shape: 'mesh',
				skip: this.skip,
				colorDepth: 'auto'
			},
			worker: false
		});
		return meshToGeometry(mesh);
	}

}

export { LAZLoader };
