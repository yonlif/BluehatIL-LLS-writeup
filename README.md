# BluehatIL LLS writeup
A writeup solution for the "Cracking LLS (Locker Layer Security)" challenge in the BluehatIL 2025 conference. **[@Danlif](https://github.com/Danlif1/Danlif1)** and I solved this challenge together a few days after the conference (Was very fun! The conference and the challenge).

## Challenge description
> We’ve installed state-of-the-art cryptography in our faculty lockers. They run on a newly invented “Locker Layer Security” protocol. Best of luck opening them... unless, of course, you're holding the real key (or something better).

## TL;DR
The challenge requires an understading of [elliptic curves cryptography](https://en.wikipedia.org/wiki/Elliptic_curve). We review some ideas to the solution and then use the fact that the code does [not verify that a point is on the curve](https://github.com/elikaski/ECC_Attacks?tab=readme-ov-file#Not-verifying-that-a-point-is-on-the-curve). To solve the challenge yourself you will need sage, go ahead and [install](https://doc.sagemath.org/html/en/installation/index.html) it now since it is about 1GB...

## Starting the challenge

Scanning the QR code we get "blue-lockers.tar". Inside there are the following go files:
* `point.go` - Implementation of elliptic curve point and related math
* `sm2.go` - Implementation of cryptography on ellipitc curves, ECHD and such. Also the EC parameters the code uses.
* `galois_field.go` - Literally opened this file only twice - Some math related to EC implementing a finite field.
* `lls.go` - The most interesting file - contains a handshake - encryption and authentication client and server.
* `server/main.go` - The server that is running in the event - getting a private key from environment variable, listening on port `8080` and has 2 endpoints - `info` and `open`. Both endpoints actually starts with handshake happaning under the hood using the LLS Listener. The `info` function returns the public key of the server and the client and open checks if the public key of the client and the server is the same and if so - opens the locker. The catch? If you pass the public key of the server you will not know the private key (since we didn't choose it) and will not be able to pass authentication.
* `client/main.go` - Not very interesing, using `lls.go` to communicate with the server.

### Diving into `lls.go`

## Attack ideas
We had a few ideas, frankly afer a few minutes we just dove into the crypto (Also checked for the stupid go bug where you create a variable without `:=`, here is a [liveoverflow](https://www.youtube.com/watch?v=wVknDjTgQoo&ab_channel=LiveOverflow) video about it, he also was at the event!!). Looking back maybe checking the mutexs could have been a good idea. We starting to think - the fact that the ECDH and ECDSA both initialized with the same key was also interesting but we couldn't exploit anything from it.

### ECDSA No validation idea
The following idea was cool but did not solve the CTF, you can skip reading if you are here for the solution.  

### 
