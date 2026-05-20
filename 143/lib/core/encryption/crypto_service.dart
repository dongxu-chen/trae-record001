import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';
import 'package:crypto/crypto.dart';
import 'package:pointycastle/export.dart';

class CryptoService {
  static const int _keySize = 32;
  static const int _nonceSize = 12;
  static const int _tagSize = 16;

  Uint8List deriveKey(String passphrase, String salt, {int iterations = 100000}) {
    final pbkdf2 = PBKDF2KeyDerivator(HMac(SHA256Digest(), 64))
      ..init(Pbkdf2Parameters(
        utf8.encode(salt) as Uint8List,
        iterations,
        _keySize,
      ));
    return pbkdf2.process(utf8.encode(passphrase) as Uint8List);
  }

  EncryptedData encrypt(Map<String, dynamic> data, Uint8List key) {
    final nonce = _generateNonce();
    final gcm = GCMBlockCipher(AESFastEngine())
      ..init(true, AEADParameters(KeyParameter(key), _tagSize * 8, nonce, Uint8List(0)));

    final plaintext = utf8.encode(json.encode(data));
    final ciphertextWithTag = gcm.process(Uint8List.fromList(plaintext));

    final ciphertext = ciphertextWithTag.sublist(0, ciphertextWithTag.length - _tagSize);
    final tag = ciphertextWithTag.sublist(ciphertextWithTag.length - _tagSize);

    return EncryptedData(
      ciphertext: base64.encode(ciphertext),
      nonce: base64.encode(nonce),
      tag: base64.encode(tag),
    );
  }

  Map<String, dynamic> decrypt(EncryptedData encrypted, Uint8List key) {
    final gcm = GCMBlockCipher(AESFastEngine())
      ..init(false, AEADParameters(
        KeyParameter(key),
        _tagSize * 8,
        base64.decode(encrypted.nonce),
        Uint8List(0),
      ));

    final ciphertextWithTag = base64.decode(encrypted.ciphertext) + base64.decode(encrypted.tag);
    final plaintext = gcm.process(ciphertextWithTag);

    return json.decode(utf8.decode(plaintext)) as Map<String, dynamic>;
  }

  String generateHMAC(String data, Uint8List key) {
    final hmac = Hmac(sha256, key);
    final digest = hmac.convert(utf8.encode(data));
    return base64.encode(digest.bytes);
  }

  bool verifyHMAC(String data, String signature, Uint8List key) {
    final expected = generateHMAC(data, key);
    return constantTimeCompare(signature, expected);
  }

  bool constantTimeCompare(String a, String b) {
    if (a.length != b.length) return false;
    var result = 0;
    for (var i = 0; i < a.length; i++) {
      result |= a.codeUnitAt(i) ^ b.codeUnitAt(i);
    }
    return result == 0;
  }

  Uint8List _generateNonce() {
    final random = Random.secure();
    return Uint8List.fromList(List.generate(_nonceSize, (_) => random.nextInt(256)));
  }

  String generateNonceString() {
    return base64.encode(_generateNonce());
  }

  KeyPair generateKeyPair() {
    final keyGen = ECKeyGenerator()
      ..init(ParametersWithRandom(
        ECKeyGeneratorParameters(ECCurve_secp256r1()),
        SecureRandom('Fortuna')..seed(KeyParameter(_generateNonce())),
      ));

    final pair = keyGen.generateKeyPair();
    final privKey = pair.privateKey as ECPrivateKey;
    final pubKey = pair.publicKey as ECPublicKey;

    return KeyPair(
      privateKey: _encodeBigInt(privKey.d!),
      publicKey: _encodeBigInt(pubKey.Q!.x!.toBigInteger()!) + '.' + _encodeBigInt(pubKey.Q!.y!.toBigInteger()!),
    );
  }

  Uint8List deriveSharedSecret(String privateKey, String publicKey) {
    final privD = _decodeBigInt(privateKey);
    final pubParts = publicKey.split('.');
    final pubX = _decodeBigInt(pubParts[0]);
    final pubY = _decodeBigInt(pubParts[1]);

    final curve = ECCurve_secp256r1();
    final Q = ECPoint(curve, curve.fromBigInteger(pubX), curve.fromBigInteger(pubY));
    final privParams = ECPrivateKeyParameters(privD, ECDomainParameters('prime256v1'));
    final pubParams = ECPublicKeyParameters(Q, ECDomainParameters('prime256v1'));

    final agreement = ECDHAgreement()
      ..init(privParams);
    final sharedSecret = agreement.calculateAgreement(pubParams);

    final sha256 = SHA256Digest();
    return sha256.process(sharedSecret);
  }

  String _encodeBigInt(BigInt bigInt) {
    return bigInt.toRadixString(16).padLeft(64, '0');
  }

  BigInt _decodeBigInt(String hex) {
    return BigInt.parse(hex, radix: 16);
  }

  String hashData(String data) {
    return sha256.convert(utf8.encode(data)).toString();
  }

  String hashMap(Map<String, dynamic> map) {
    final sortedKeys = map.keys.toList()..sort();
    final buffer = StringBuffer();
    for (final key in sortedKeys) {
      buffer.write('$key:${map[key]};');
    }
    return hashData(buffer.toString());
  }
}

class EncryptedData {
  final String ciphertext;
  final String nonce;
  final String tag;

  EncryptedData({
    required this.ciphertext,
    required this.nonce,
    required this.tag,
  });

  Map<String, dynamic> toJson() => {
    'ciphertext': ciphertext,
    'nonce': nonce,
    'tag': tag,
  };

  factory EncryptedData.fromJson(Map<String, dynamic> json) => EncryptedData(
    ciphertext: json['ciphertext'] as String,
    nonce: json['nonce'] as String,
    tag: json['tag'] as String,
  );
}

class KeyPair {
  final String privateKey;
  final String publicKey;

  KeyPair({required this.privateKey, required this.publicKey});
}
