# BluehatIL LLS writeup
A writeup solution for the "Cracking LLS (Locker Layer Security)" challenge in the BluehatIL 2025 conference. **[@Danlif](https://github.com/Danlif1/Danlif1)** and I solved this challenge together a few days after the conference (Was very fun! The conference and the challenge).

## Challenge description
> We’ve installed state-of-the-art cryptography in our faculty lockers. They run on a newly invented “Locker Layer Security” protocol. Best of luck opening them... unless, of course, you're holding the real key (or something better).

## TL;DR
The challenge requires an understanding of [elliptic curves cryptography](https://en.wikipedia.org/wiki/Elliptic_curve). We review some ideas for the solution and then use the fact that the code does [not verify that a point is on the curve](https://github.com/elikaski/ECC_Attacks?tab=readme-ov-file#Not-verifying-that-a-point-is-on-the-curve). To solve the challenge yourself, you will need sage, go ahead and [install](https://doc.sagemath.org/html/en/installation/index.html) it now since it is about 1GB...

## Starting the challenge

Scanning the QR code, we get "blue-lockers.tar". Inside, there are the following go files:
* `point.go` - Implementation of elliptic curve point and related math
* `sm2.go` - Implementation of cryptography on elliptic curves, ECHD, and such. Also, the EC parameters the code uses.
* `galois_field.go` - Literally opened this file only twice - Some math related to EC implementing a finite field.
* `lls.go` - The most interesting file - contains a handshake - encryption and authentication client and server.
* `server/main.go` - The server that is running in the event - getting a private key from environment variable, listening on port `8080` and has 2 endpoints - `info` and `open`. Both endpoints actually start with a handshake happening under the hood using the LLS Listener. The `info` function returns the public key of the server and the client and open checks if the public key of the client and the server is the same and if so - opens the locker. The catch? If you pass the public key of the server you will not know the private key (since we didn't choose it) and will not be able to pass authentication.
* `client/main.go` - Not very interesting, using `lls.go` to communicate with the server.

### Diving into `lls.go`

```
// LLS Protocol - elliptic curve Locker Layer Security (SM2)
// On new connection, perform the following handshake:
// 1. Establisha  secure channel using ECDH
// 2. Apply AES-CTR encryption using shared secret
// 3. Exchange signature blocks for authentication
// 4. Done! Locker Layer Security connection established
```
So this comment gives us the general idea.  
We start with generating `ecdh` and `ecdsa` objects, `ecdh` will be used for key exchange (1) to create encrypted AES channel, `ecdsa` will be used to verify signature blocks (3).  
Both the client and the server are sending the public key, multipling it by the private key, applying `sha256` and this is the shared AES key.  

![An-example-of-ECC-version-of-Diffie-Hellman-Protocol](https://github.com/user-attachments/assets/92de61eb-132e-4761-a47f-e53815f33b12)

An understanding of the ECDH algorithm is important here - you can read in wikipedia about the [general idea](https://en.wikipedia.org/wiki/Diffie%E2%80%93Hellman_key_exchange) and the [EC variant](https://en.wikipedia.org/wiki/Elliptic-curve_Diffie%E2%80%93Hellman). Shortly - an elliptic curve point is a mathematical object that implements the "Addition" operator between two points. Multiplication is defined only point to scalar and is implemented by adding the point to itself many times. Both of these operations create another point on curve. If we multiplied a point by a scalar it should be hard to find the original point (This is the discrete logarithm problem in elliptic curve, many CTFs simply use a curve where for some magic math reasons solving this is easy but in this CTF the curve is SM2 - and is the [Chinese national standard](https://docs.openssl.org/1.1.1/man7/SM2/#name)).

So, client sends to server his public key - `client_private_key * G (G = an aggreed point from the beggining)` and the server multiplies by `server_private_key` resulting in `client_private_key * server_private_key * G`. Take a moment to understand why the client gets the same expression on his side as well.

Under the new AES layer - the server is signing on the string "LlsServerHello:" and the client verifies. Than the client sends a signature over "LlsClientHello:". If the server 

## Attack ideas

We had a few ideas, Frankly after a few minutes we just dove into the crypto (Also checked for the stupid go bug where you create a variable without `:=`, Here is a [liveoverflow](https://www.youtube.com/watch?v=wVknDjTgQoo&ab_channel=LiveOverflow) video about it, he also was at the event!!). Looking back maybe checking the mutexs could have been a good idea. We starting to think - the fact that the ECDH and ECDSA both initialized with the same key was also interesting, but we couldn't exploit anything from it.

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

### 
