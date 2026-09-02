;; ULPF WASM proof-of-concept parser (Module 21).
;;
;; Parses a pipe-delimited line   ts|host|user|src_ip|action   into the JSON
;;   {"timestamp":"..","host":"..","username":"..","source_ip":"..","action":".."}
;;
;; It imports NOTHING (no WASI, no host functions) and only touches its own
;; linear memory. The host runs it under fuel + epoch-timeout + memory limits.
;;
;; ABI:
;;   (export "memory")
;;   (func (export "alloc")      (param i32) (result i32))
;;   (func (export "ulpf_parse") (param i32 i32) (result i64))
;;       returns (out_ptr << 32) | out_len
(module
  (memory (export "memory") 4)

  ;; fragment blob = the five key fragments concatenated (also happens to be
  ;; the valid "all empty" JSON):
  ;;   {"timestamp":"","host":"","username":"","source_ip":"","action":""}
  (data (i32.const 0)
    "{\22timestamp\22:\22\22,\22host\22:\22\22,\22username\22:\22\22,\22source_ip\22:\22\22,\22action\22:\22\22}")

  ;; fragment table at offset 128: 6 * (i32 offset, i32 length), little-endian
  (data (i32.const 128)
    "\00\00\00\00\0e\00\00\00"   ;; frag0 {"timestamp":"      off 0  len 14
    "\0e\00\00\00\0a\00\00\00"   ;; frag1 ","host":"           off 14 len 10
    "\18\00\00\00\0e\00\00\00"   ;; frag2 ","username":"       off 24 len 14
    "\26\00\00\00\0f\00\00\00"   ;; frag3 ","source_ip":"      off 38 len 15
    "\35\00\00\00\0c\00\00\00"   ;; frag4 ","action":"         off 53 len 12
    "\41\00\00\00\02\00\00\00")  ;; end   "}                   off 65 len 2

  (global $heap (mut i32) (i32.const 8192))

  ;; bump allocator, 8-byte aligned
  (func $alloc (export "alloc") (param $n i32) (result i32)
    (local $p i32)
    (local.set $p (global.get $heap))
    (global.set $heap
      (i32.and
        (i32.add (i32.add (global.get $heap) (local.get $n)) (i32.const 7))
        (i32.const -8)))
    (local.get $p))

  ;; copy $n bytes from $src to $dst ; returns $dst + $n
  (func $memcpy (param $dst i32) (param $src i32) (param $n i32) (result i32)
    (local $i i32)
    (block $done
      (loop $l
        (br_if $done (i32.ge_u (local.get $i) (local.get $n)))
        (i32.store8
          (i32.add (local.get $dst) (local.get $i))
          (i32.load8_u (i32.add (local.get $src) (local.get $i))))
        (local.set $i (i32.add (local.get $i) (i32.const 1)))
        (br $l)))
    (i32.add (local.get $dst) (local.get $n)))

  ;; write fragment #$idx at $w ; returns new write cursor
  (func $wfrag (param $w i32) (param $idx i32) (result i32)
    (local $meta i32)
    (local.set $meta (i32.add (i32.const 128) (i32.mul (local.get $idx) (i32.const 8))))
    (call $memcpy
      (local.get $w)
      (i32.load (local.get $meta))
      (i32.load (i32.add (local.get $meta) (i32.const 4)))))

  (func $ulpf_parse (export "ulpf_parse") (param $ptr i32) (param $len i32) (result i64)
    (local $out i32)
    (local $w i32)
    (local $r i32)
    (local $rend i32)
    (local $field i32)
    (local $c i32)

    ;; output buffer: worst case = input escaped x2 + fragments (67) + slack
    (local.set $out
      (call $alloc (i32.add (i32.mul (local.get $len) (i32.const 2)) (i32.const 128))))
    (local.set $w (local.get $out))
    (local.set $r (local.get $ptr))
    (local.set $rend (i32.add (local.get $ptr) (local.get $len)))
    (local.set $field (i32.const 0))

    ;; leading fragment {"timestamp":"
    (local.set $w (call $wfrag (local.get $w) (i32.const 0)))

    (block $end
      (loop $scan
        (br_if $end (i32.ge_u (local.get $r) (local.get $rend)))
        (local.set $c (i32.load8_u (local.get $r)))

        ;; '|' 0x7C -> next field (max 4 delimiters)
        (if (i32.and (i32.eq (local.get $c) (i32.const 124))
                     (i32.lt_u (local.get $field) (i32.const 4)))
          (then
            (local.set $field (i32.add (local.get $field) (i32.const 1)))
            (local.set $w (call $wfrag (local.get $w) (local.get $field)))
            (local.set $r (i32.add (local.get $r) (i32.const 1)))
            (br $scan)))

        ;; '"' 0x22 or '\' 0x5C -> escape
        (if (i32.or (i32.eq (local.get $c) (i32.const 34))
                    (i32.eq (local.get $c) (i32.const 92)))
          (then
            (i32.store8 (local.get $w) (i32.const 92))
            (local.set $w (i32.add (local.get $w) (i32.const 1)))
            (i32.store8 (local.get $w) (local.get $c))
            (local.set $w (i32.add (local.get $w) (i32.const 1)))
            (local.set $r (i32.add (local.get $r) (i32.const 1)))
            (br $scan)))

        ;; printable (>= 0x20) -> copy ; control chars are dropped
        (if (i32.ge_u (local.get $c) (i32.const 32))
          (then
            (i32.store8 (local.get $w) (local.get $c))
            (local.set $w (i32.add (local.get $w) (i32.const 1)))))

        (local.set $r (i32.add (local.get $r) (i32.const 1)))
        (br $scan)))

    ;; pad any missing fields so the JSON stays well-formed
    (block $pdone
      (loop $pad
        (br_if $pdone (i32.ge_u (local.get $field) (i32.const 4)))
        (local.set $field (i32.add (local.get $field) (i32.const 1)))
        (local.set $w (call $wfrag (local.get $w) (local.get $field)))
        (br $pad)))

    ;; trailing "}"
    (local.set $w (call $wfrag (local.get $w) (i32.const 5)))

    (i64.or
      (i64.shl (i64.extend_i32_u (local.get $out)) (i64.const 32))
      (i64.extend_i32_u (i32.sub (local.get $w) (local.get $out)))))
)
