// Lift the person out of a portrait with macOS Vision and save it as a PNG with a soft alpha mask.
// Usage: swift cutout.swift in.jpg out.png [in2.jpg out2.png ...]
import AppKit
import CoreImage
import Vision

let ctx = CIContext()

func cutout(_ inPath: String, _ outPath: String) throws {
    guard let src = CIImage(contentsOf: URL(fileURLWithPath: inPath)) else {
        throw NSError(domain: "cutout", code: 1, userInfo: [NSLocalizedDescriptionKey: "cannot read \(inPath)"])
    }
    let handler = VNImageRequestHandler(ciImage: src)
    let req = VNGenerateForegroundInstanceMaskRequest()
    try handler.perform([req])
    guard let obs = req.results?.first, !obs.allInstances.isEmpty else {
        throw NSError(domain: "cutout", code: 2, userInfo: [NSLocalizedDescriptionKey: "no subject in \(inPath)"])
    }
    let buf = try obs.generateMaskedImage(ofInstances: obs.allInstances, from: handler, croppedToInstancesExtent: false)
    let out = CIImage(cvPixelBuffer: buf)
    let cs = CGColorSpace(name: CGColorSpace.sRGB)!
    try ctx.writePNGRepresentation(of: out, to: URL(fileURLWithPath: outPath), format: .RGBA8, colorSpace: cs)
}

let args = Array(CommandLine.arguments.dropFirst())
var failed = 0
for i in stride(from: 0, to: args.count - 1, by: 2) {
    do { try cutout(args[i], args[i + 1]) } catch { print("FAIL", error.localizedDescription); failed += 1 }
}
print("cutouts done, failed \(failed)")
