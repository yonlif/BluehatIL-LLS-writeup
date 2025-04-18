# BluehatIL LLS writeup
A writeup solution for the "Cracking LLS (Locker Layer Security)" challenge in the BluehatIL 2025 conference. **[@Danlif](https://github.com/Danlif1/Danlif1)** and I solved this challenge together a few days after the conference (Was very fun! the conference and the challenge).

This writeup does not go straight to the point but explains the solution and our way of thinking. It also adds a bit of elliptic curve explanations and is hopefully suitable for people with little to no background. If you have any questions, feel free to send an issue.

## Challenge description
> We’ve installed state-of-the-art cryptography in our faculty lockers. They run on a newly invented “Locker Layer Security” protocol. Best of luck opening them... unless, of course, you're holding the real key (or something better).

## TL;DR
The challenge requires an understanding of [elliptic curves cryptography](https://en.wikipedia.org/wiki/Elliptic_curve). We review some ideas for the solution and then use the fact that the code does [not verify that a point is on the curve](https://github.com/elikaski/ECC_Attacks?tab=readme-ov-file#Not-verifying-that-a-point-is-on-the-curve). To solve the challenge yourself, you will need SageMath, an open-source mathematics software. Go ahead and [install](https://doc.sagemath.org/html/en/installation/index.html) it now since it is about 1GB...

## Starting the challenge

Scanning the QR code, we get "blue-lockers.tar". Inside, there are the following go files:
* `point.go` - Implementation of elliptic curve point and related math
* `sm2.go` - Implementation of cryptography on elliptic curves, ECHD, and such. Also, the EC parameters the code uses.
* `galois_field.go` - Literally opened this file only twice - Some math related to EC implementing a finite field.
* `lls.go` - The most interesting file - contains a handshake - encryption and authentication client and server.
* `server/main.go` - The server that is running in the event - getting a private key from the environment variable, listening on port `8080` and has 2 endpoints - `info` and `open`. Both endpoints actually start with a handshake happening under the hood using the LLS Listener. The `info` function returns the public key of the server and the client and `open` checks if the public key of the client and the server is the same and if so - opens the locker. The catch? If you pass the public key of the server you will not know the private key (since we didn't choose it) and will not be able to pass authentication.
* `client/main.go` - Not very interesting, using `lls.go` to communicate with the server.

### Diving into `lls.go`

```
// LLS Protocol - elliptic curve Locker Layer Security (SM2)
// On new connection, perform the following handshake:
// 1. Establish secure channel using ECDH
// 2. Apply AES-CTR encryption using shared secret
// 3. Exchange signature blocks for authentication
// 4. Done! Locker Layer Security connection established
```
So this comment gives us a general idea.  
We start with generating `ecdh` and `ecdsa` objects, `ecdh` will be used for key exchange (stage 1 from the comment above) to create an encrypted AES channel, `ecdsa` will be used to verify signature blocks (stage 3).  
Both the client and the server are sending the public key, multiplying it by the private key, and applying `sha256`, and this is the shared AES key.  

![An-example-of-ECC-version-of-Diffie-Hellman-Protocol](https://github.com/user-attachments/assets/92de61eb-132e-4761-a47f-e53815f33b12)

An understanding of the ECDH algorithm is important here - you can read in wikipedia about the [general idea](https://en.wikipedia.org/wiki/Diffie%E2%80%93Hellman_key_exchange) and the [EC variant](https://en.wikipedia.org/wiki/Elliptic-curve_Diffie%E2%80%93Hellman). Shortly - an elliptic curve point is a mathematical object that implements the "Addition" operator between two points. Multiplication is defined only point to scalar and is implemented by adding the point to itself many times. Both of these operations create another point on the curve. If we multiplied a point by a scalar it should be hard to find the original point (This is the discrete logarithm problem in elliptic curve, many CTFs simply use a curve where for some magic math reasons solving this is easy but in this CTF the curve is SM2 - and is the [Chinese national standard](https://docs.openssl.org/1.1.1/man7/SM2/#name)).

So, the client sends to the server his public key - `client_private_key * G (G = an aggreed point from the beggining)` and the server multiplies by `server_private_key` resulting in `client_private_key * server_private_key * G`. Take a moment to understand why the client gets the same expression on his side as well.

Under the new AES layer - the server signs on the string "LlsServerHello:" and the client verifies. Then the client sends a signature over "LlsClientHello:". If the server successfully validates the signature, it sets the client public key as `peerPublicKey`, as mentioned before, if the `peerPublicKey` is equal to `publicKey`, the door will open. The validation happens with the `ecdsa` object and is explained in more detail later. 

## Attack ideas

We had a few ideas. Frankly, after a few minutes, we just dove into the crypto (Also checked for the stupid go bug where you create a variable without `:=`, Here is a [liveoverflow](https://www.youtube.com/watch?v=wVknDjTgQoo&ab_channel=LiveOverflow) video about it, he also was at the event!!). Looking back maybe checking the mutexs could have been a good idea. We starting to think - the fact that the ECDH and ECDSA both initialized with the same key was also interesting, but we couldn't exploit anything from it.

### ECDSA No validation idea
The following idea was cool but did not solve the CTF, you can skip reading if you are here for the solution.  
The function `Verify` is meant to verify that the signature is correct.
The function takes 4 variables:
* `message` - Which is the original message in the signature
* `publicKey` - This is the public key used (In our case, this is the server's public key)
* `r` - This is the `nonce` We used for the signature.
* `s` - This is the resulting signature.

In the [Wikipedia page](https://en.wikipedia.org/wiki/Elliptic_Curve_Digital_Signature_Algorithm), we can see that one of the demands is to `Verify that r and s are integers in [1,n−1].`
Which isn't being done in the code.

If we will pass the value `r = 0`, We can get that the last line of: `if big.NewInt(0).Mod(&r, n).Cmp(&res.x.Int) == 0` actually demands: `res.x.Int == 0`

Looking at how `res` is calculated, we can see that if `s_Inverse` was able to be equal to `0`, then `res` would be equal to `0`

`s_Inverse` is equal to `new(big.Int).ModInverse(&s, n)` as we control `s` we thought that we might be able to find a value `s` such that it would be equal `0` (Or maybe any other unwanted value `<=0`)

If we give `s = 0` to the expression `new(big.Int).ModInverse(&s, n)` We will get `nil` </br> which crashes us in the next line: `u1 := new(big.Int).Mul(z, s_Inverse)` because of `runtime error: invalid memory address or nil pointer dereference`

If we try to give `s < 0` or `s > n` to the expression, we will get the same values as if `s` was in range.

So even though no checks on `r` nor `s` were performed - the verification code seems valid. :(

### Leaking the key
After understanding the ECDSA bypass will not work and validating the rest of the implementation follows the Wikipedia instructions (like checking that k is generated from a secure random at signing), we went to another part of the program that seems suspicious. We noticed from the beginning that no one validates that the given point is on the curve - there is a function `pointt.go:IsOnCurve` that is never called. But in the ECDSA validation there was nothing to do with that (the point must be the server public key).

Where else can we use this fact? In the key exchange, we pass a point!

![elliptic_key_addititon](https://github.com/user-attachments/assets/f0a475da-ef98-4b56-8eac-1f924c51d06f)
> Nice illustration of elliptic key addition from [bitcoin stackexchange](https://bitcoin.stackexchange.com/a/38923)

To understand the exploit, this is what you need to know:
* There is a finite number of points on a cryptographic elliptic curve - all are pairs X,Y of integers
* The number of points on the curve is called N and is easy to calculate
* G is called the generator - adding G to itself will pass through all the points on the curve untill returning to itself.
* Since adding two points results in another point on the curve - if the curve order is 2, adding G to itself over and over will result in a loop between two values in this specific curve.
* If the order of the curve is some number, say `1837 * 2`, we can choose `new_G = G * 1837`, and adding new_G to itself will result in the same effect.
* Last and most tricky one to understand - Given a point on curve X (mod P) and another point on curve Y (mod P) - the operations performed to calculate new points on these curves are the same. It simply will create points on the curve you started at, but the math we do is the same.

With this understanding, we will leak the last bit of the private key. Let's remember that we multiply the point we give by the private key. If the point is in a curve of order 2 - there are only 2 options for the derived key, and the parity bit of the key will decide which one it will be! The key will be used to encrypt and send the string `"LlsServerHello:<Some signature bytes>"` we will iterate over all the key options (2 options) and will find which one decrypts the beginning correctly. This will give us the last bit of the key.

The last thing we need to do in order to solve is use the [Chinese remainder theorem](https://en.wikipedia.org/wiki/Chinese_remainder_theorem), the intuition for this goes as follows - if for a single value x (private key) we can create equations that leak information on that key on many different modulus we can recreate the original x. For example, if `x = 1 mod 2` and `x = 2 mod 3`, then x can be 5. The CRT gives us a way to recreate x from these equations, there is a proof but [this margin is too narrow to contain](https://en.wikipedia.org/wiki/Fermat%27s_Last_Theorem#Fermat's_conjecture). So we will generate multiple points of small orders, check what is the remainder of the private key from that order, and will create equations for the CRT. We will use `sage` in the implementation to do all the CRT and EC heavy lifting. That will recreate the private key!

Given the private key - winning is trivial, use the given go client and put the private key in the correct environment variable.

All of the used code is in the repository (partially commented lol), now you can use and understand it. It is recommanded to read some more about elliptic curves to better understand the lies we told to "pop science explain" the exploit :)
